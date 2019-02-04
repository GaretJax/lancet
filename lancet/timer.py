from datetime import date
from urllib.parse import urljoin

from .utils import cached_property

import requests

import attr


@attr.s
class HarvestError(Exception):
    error = attr.ib()
    message = attr.ib()


class HarvestAPI:
    def __init__(self, server, basic_auth):
        self.server = server
        self._projects = None
        self._session = requests.Session()
        self._session.headers = {
            "user-agent": "lancet",
            "accept": "application/json",
            "content-type": "application/json",
            "harvest-account-id": basic_auth[0],
            "authorization": f"bearer {basic_auth[1]}",
        }

    def _paginate(self, url, key, params=None):
        while url:
            page = self._request("get", url, params=params)
            yield from page[key]
            url = page["links"]["next"]

    def _request(self, method, url, params=None, json=None):
        r = self._session.request(
            method, urljoin(self.server, url), params=params, json=json
        )
        payload = r.json()
        if r.status_code not in [200, 201]:
            raise HarvestError(payload["error"], payload["error_description"])
        return payload

    def restart(self, id):
        return self._request("patch", f"time_entries/{id}/restart")

    def stop(self, id):
        return self._request("patch", f"time_entries/{id}/stop")

    def pause(self, id=None):
        for entry in self.daily(is_running=True):
            if id is None or id == entry["id"]:
                self.stop(entry["id"])
            break
        else:
            # No running timers
            pass

    def whoami(self):
        return self._request("get", "users/me")

    @cached_property
    def user_id(self):
        return self.whoami()["id"]

    def projects(self):
        if not self._projects:
            self._projects = list(self._paginate("projects", "projects"))
        return self._projects

    def tasks(self, project_id):
        for assignment in self._paginate(
            f"projects/{project_id}/task_assignments", "task_assignments"
        ):
            yield assignment["task"]

    def daily(self, is_running=None):
        today = date.today().isoformat()
        filters = {"from": today, "to": today, "user_id": self.user_id}
        if is_running is not None:
            filters["is_running"] = str(bool(is_running)).lower()
        return self._paginate("time_entries", "time_entries", params=filters)

    def close(self):
        self._session.close()


class HarvestPlatform(HarvestAPI):
    def __init__(self, server, basic_auth, project_id_getter, task_id_getter):
        self.get_project_id = project_id_getter
        self.get_task_id = task_id_getter
        super().__init__(server, basic_auth)

    def start(self, issue, resume=True):
        if resume:
            timers = list(self.daily())
            for entry in reversed(timers):
                ext = entry.get("external_reference", None)
                if not ext:
                    continue
                if ext["group_id"] != str(issue.project.id):
                    continue
                if ext["id"] != str(issue.id):
                    continue

                if not entry["is_running"]:
                    self.restart(entry["id"])
                return

        name = "{} - {}".format(issue.id, issue.summary)
        project_id = self.get_project_id(self, issue)
        task_id = self.get_task_id(self, project_id, issue)
        self._request(
            "post",
            "time_entries",
            json={
                "external_reference": {
                    "group_id": issue.project.id,
                    "id": issue.id,
                    "permalink": issue.link,
                },
                "hours": 0,
                "notes": name,
                "project_id": project_id,
                "task_id": task_id,
                "spent_date": date.today().isoformat(),
            },
        )


class MappedProjectID:
    def __init__(self, project_ids):
        self._project_ids = project_ids

    @classmethod
    def fromstring(cls, string):
        if not string:
            return cls({})
        project_ids = string.split(",")
        project_ids = (p.split(":") for p in project_ids)
        project_ids = ((None, p[0]) if len(p) == 1 else p for p in project_ids)
        project_ids = ((k, int(v)) for k, v in project_ids if v)
        project_ids = dict(project_ids)
        return cls(project_ids)

    def get_issue_project_id(self, issue):
        return self._project_ids.get(str(issue.type))

    def __call__(self, timer, issue):
        project_id = self.get_issue_project_id(issue)

        # If the issue did not match any explicitly defined project and it is
        # a subtask, get the parent issue
        if not project_id and issue.is_subtask:
            parent = issue.get_parent()
            project_id = self.get_issue_project_id(parent)

        # If no project was found yet, get the default project
        if not project_id:
            project_id = self._project_ids.get(None)

        # At this point, if we didn't get a project, then it's an error
        if not project_id:
            raise ValueError(
                'Could not find a project ID for issue type "{}"'.format(
                    issue.type
                )
            )

        return project_id


def mapped_project_id_getter(lancet):
    return MappedProjectID.fromstring(lancet.config.get("timer", "project_id"))


def fixed_task_id_getter(lancet):
    def getter(timer, project_id, issue):
        return int(lancet.config.get("timer", "task_id"))

    return getter


class EpicTaskMapper:
    def __init__(self, epic_link_field, epic_name_field):
        self.epic_link_field = epic_link_field
        self.epic_name_field = epic_name_field

    def get_epic(self, issue):
        return issue.get_epic()

    def __call__(self, timer, project_id, issue):
        try:
            epic = self.get_epic(issue)
        except Exception:
            raise ValueError(
                "Could not find the epic for task {}".format(issue.key)
            )
        epic_name = getattr(epic.fields, self.epic_name_field)

        for t in timer.tasks(project_id):
            if t["name"] == epic_name:
                return t["id"]

        raise ValueError(
            'Could not find a task with the name "{}" in the Harvest project '
            "with ID {}".format(epic_name, project_id)
        )


def epic_task_id_getter(lancet):
    return EpicTaskMapper(
        lancet.config.get("harvest", "epic_link_field"),
        lancet.config.get("harvest", "epic_name_field"),
    )


def credentials_checker(url, username, password):
    """Check the provided credentials using the Harvest API."""
    api = HarvestAPI(url, (username, password))
    try:
        api.whoami()
    except HarvestError:
        return False
    else:
        return True


def harvest(lancet, config_section):
    """Construct a new Harvest client."""
    url, username, password = lancet.get_credentials(
        config_section, credentials_checker
    )

    project_id_getter = lancet.get_instance_from_config(
        "timer", "project_id_getter", lancet
    )
    task_id_getter = lancet.get_instance_from_config(
        "timer", "task_id_getter", lancet
    )

    client = HarvestPlatform(
        server=url,
        basic_auth=(username, password),
        project_id_getter=project_id_getter,
        task_id_getter=task_id_getter,
    )
    lancet.call_on_close(client.close)
    return client
