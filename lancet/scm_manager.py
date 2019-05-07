import attr
from urllib.parse import quote as urlquote

from giturlparse import parse as giturlparse

from gitlab.exceptions import GitlabCreateError


class SCMManager:
    def create_pull_request(self, branch, base_branch, summary, description):
        raise NotImplementedError


class PullRequest:
    @property
    def link(self):
        raise NotImplementedError

    def assign_to(self, username):
        raise NotImplementedError


@attr.s
class PullRequestAlreadyExists(Exception):
    pull_request = attr.ib()


@attr.s
class GitlabSCMManager(SCMManager):
    api = attr.ib()
    repo = attr.ib()
    remote_name = attr.ib()

    def create_pull_request(
        self, source_branch, target_branch, summary, description
    ):
        remote = self.repo.lookup_remote(self.remote_name)
        project_path = giturlparse(remote.url).pathname
        if project_path.endswith(".git"):
            project_path = project_path[:-4]
        prj = self.api.projects.get(urlquote(project_path))
        try:
            mr = prj.mergerequests.create(
                {
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                    "title": summary,
                    "description": description,
                    "remove_source_branch": True,
                }
            )
        except GitlabCreateError as e:
            if e.error_message and "already exists" in e.error_message[0]:
                # TODO: fetch PR and pass in
                raise PullRequestAlreadyExists(None)
        return GitlabPullRequest(self, mr)


@attr.s
class GitlabPullRequest(PullRequest):
    manager = attr.ib()
    merge_request = attr.ib()

    @property
    def link(self):
        return self.merge_request.web_url

    def assign_to(self, username):
        user = self.manager.api.users.list(username=username)[0]
        self.merge_request.assignee_id = user.id
        self.merge_request.save()


def gitlab(lancet, config_section):
    from gitlab import Gitlab as GitlabAPI

    url, username, private_token = lancet.get_credentials(config_section)
    api = GitlabAPI(url, private_token=private_token)
    return GitlabSCMManager(
        api, lancet.repo, lancet.config.get("repository", "remote_name")
    )
