import attr

from .utils import cached_property


def notimplementedproperty():
    @property
    def accessor(self):
        raise NotImplementedError

    return accessor


class Tracker:
    def create_issue(self, title):
        raise NotImplementedError

    def get_issue(self, issue_id):
        raise NotImplementedError

    def whoami(self):
        raise NotImplementedError


class Project:
    id = notimplementedproperty()
    name = notimplementedproperty()


class Issue:
    id = notimplementedproperty()
    summary = notimplementedproperty()
    status = notimplementedproperty()
    type = notimplementedproperty()
    assignees = notimplementedproperty()
    project = notimplementedproperty()
    is_subtask = notimplementedproperty()
    link = notimplementedproperty()

    def get_transitions(self):
        raise NotImplementedError

    def assign_to(self, username):
        raise NotImplementedError

    def apply_transition(self, transition):
        raise NotImplementedError

    def get_parent(self):
        raise NotImplementedError

    def get_epic(self):
        raise NotImplementedError


@attr.s
class GitlabTracker(Tracker):
    api = attr.ib()


def gitlab(lancet, config_section):
    from gitlab import Gitlab as GitlabAPI

    url, username, private_token = lancet.get_credentials(config_section)
    api = GitlabAPI(url, private_token=private_token)
    return GitlabTracker(api)


@attr.s
class JIRATracker(Tracker):
    api = attr.ib()
    board_id = attr.ib()

    def create_issue(self, project_id, summary, add_to_active_sprint=False):
        issue = self.api.create_issue(
            project=project_id, issuetype="Task", summary=summary
        )
        if add_to_active_sprint:
            active_sprints = self.api.sprints(self.board_id, state="active")
            self.api.add_issues_to_sprint(active_sprints[0].id, [issue.key])
        return JIRAIssue(self, issue)

    def get_issue(self, project_id, issue_id):
        return JIRAIssue(self, self.api.issue(issue_id))

    def whoami(self):
        return self.api.current_user()


@attr.s(cmp=False)
class JIRAProject(Project):
    tracker = attr.ib()
    project = attr.ib()

    @property
    def id(self):
        return self.project.key

    @property
    def name(self):
        return self.project.name


@attr.s(cmp=False)
class JIRAIssue(Issue):
    tracker = attr.ib()
    issue = attr.ib()

    @property
    def id(self):
        return self.issue.key

    @property
    def summary(self):
        return self.issue.fields.summary

    @property
    def status(self):
        return self.issue.fields.status.name

    @property
    def assignees(self):
        if self.issue.fields.assignee:
            return [self.issue.fields.assignee.name]
        else:
            return []

    @cached_property
    def project(self):
        return JIRAProject(self.tracker, self.issue.fields.project)

    @property
    def type(self):
        return self.issue.fields.issuetype.name

    @property
    def is_subtask(self):
        return self.issue.fields.issuetype.subtask

    @cached_property
    def link(self):
        return self.issue.permalink()

    def get_parent(self):
        if not self.is_subtask:
            return None
        parent = self.issue.__class__(self.issue._options, self.issue._session)
        parent.find(self.issue.fields.parent.key)
        return JIRAIssue(self.tracker, parent)

    def get_epic(self):
        raise NotImplementedError

        # if not self.is_subtask:
        #     return None
        # epic = self.issue.__class__(self.issue._options, self.issue._session)
        # epic.find(getattr(self.issue.fields, epic_link_field))
        # return JIRAIssue(self.tracker, parent)

    def get_transitions(self, to_status):
        if self.status == to_status:
            return []
        return [
            t
            for t in self.tracker.api.transitions(self.issue.key)
            if t["to"]["name"] == to_status
        ]

    def assign_to(self, username):
        self.tracker.api.assign_issue(self.issue.key, username)

    def apply_transition(self, transition):
        self.tracker.api.transition_issue(self.issue.key, transition["id"])


def jira(lancet, config_section):
    from jira import JIRA, JIRAError

    def checker(url, username, password):
        try:
            JIRA(options={"server": url}, basic_auth=(username, password))
        except JIRAError:
            return False
        else:
            return True

    url, username, api_token = lancet.get_credentials(config_section, checker)
    api = JIRA(
        options={"server": url, "agile_rest_path": "agile"},
        basic_auth=(username, api_token),
    )
    board_id = lancet.config.get("tracker", "board_id")
    lancet.call_on_close(api.close)
    return JIRATracker(api, board_id)
