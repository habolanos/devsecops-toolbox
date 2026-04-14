"""
Tests unitarios para azdo_pr_master_checker.py
"""

import sys
from pathlib import Path

import pytest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scm.azdo.azdo_pr_master_checker import (
    is_wildcard_branch,
    parse_branches,
    needs_local_branch_filter,
    filter_prs_by_branches,
    search_release_definitions,
    search_cds_for_repos,
    normalize,
    find_cd_candidates_for_repo,
    find_cd_by_artifact_source,
    find_cd_for_repo_with_details,
    has_stage,
)


# ═══════════════════════════════════════════════════════════════════════════════
# is_wildcard_branch
# ═══════════════════════════════════════════════════════════════════════════════
class TestIsWildcardBranch:

    @pytest.mark.unit
    def test_exact_branch(self):
        assert is_wildcard_branch("master") is False

    @pytest.mark.unit
    def test_exact_branch_qa(self):
        assert is_wildcard_branch("QA") is False

    @pytest.mark.unit
    def test_star_wildcard(self):
        assert is_wildcard_branch("release/*") is True

    @pytest.mark.unit
    def test_star_prefix_wildcard(self):
        assert is_wildcard_branch("release/v*") is True

    @pytest.mark.unit
    def test_question_wildcard(self):
        assert is_wildcard_branch("release/v?.0") is True

    @pytest.mark.unit
    def test_multiple_stars(self):
        assert is_wildcard_branch("release/*/*") is True

    @pytest.mark.unit
    def test_empty_string(self):
        assert is_wildcard_branch("") is False


# ═══════════════════════════════════════════════════════════════════════════════
# parse_branches
# ═══════════════════════════════════════════════════════════════════════════════
class TestParseBranches:

    @pytest.mark.unit
    def test_single_branch(self):
        assert parse_branches("master") == ["master"]

    @pytest.mark.unit
    def test_comma_separated(self):
        assert parse_branches("master,QA,release/*") == ["master", "QA", "release/*"]

    @pytest.mark.unit
    def test_comma_with_spaces(self):
        assert parse_branches("master, QA, release/*") == ["master", "QA", "release/*"]

    @pytest.mark.unit
    def test_all_keyword(self):
        assert parse_branches("all") == ["all"]

    @pytest.mark.unit
    def test_all_uppercase(self):
        assert parse_branches("ALL") == ["all"]

    @pytest.mark.unit
    def test_all_with_spaces(self):
        assert parse_branches("  all  ") == ["all"]


# ═══════════════════════════════════════════════════════════════════════════════
# needs_local_branch_filter
# ═══════════════════════════════════════════════════════════════════════════════
class TestNeedsLocalBranchFilter:

    @pytest.mark.unit
    def test_single_exact(self):
        assert needs_local_branch_filter(["master"]) is False

    @pytest.mark.unit
    def test_single_wildcard(self):
        assert needs_local_branch_filter(["release/*"]) is True

    @pytest.mark.unit
    def test_all(self):
        assert needs_local_branch_filter(["all"]) is True

    @pytest.mark.unit
    def test_multiple_exact(self):
        assert needs_local_branch_filter(["master", "QA"]) is True

    @pytest.mark.unit
    def test_multiple_with_wildcard(self):
        assert needs_local_branch_filter(["master", "release/*"]) is True


# ═══════════════════════════════════════════════════════════════════════════════
# filter_prs_by_branches
# ═══════════════════════════════════════════════════════════════════════════════
class TestFilterPrsByBranches:

    @pytest.mark.unit
    def test_all_no_filter(self):
        prs = [
            {"targetRefName": "refs/heads/master"},
            {"targetRefName": "refs/heads/QA"},
        ]
        result = filter_prs_by_branches(prs, ["all"])
        assert len(result) == 2

    @pytest.mark.unit
    def test_single_exact_match(self):
        prs = [
            {"targetRefName": "refs/heads/master"},
            {"targetRefName": "refs/heads/QA"},
        ]
        result = filter_prs_by_branches(prs, ["master"])
        assert len(result) == 1
        assert result[0]["targetRefName"] == "refs/heads/master"

    @pytest.mark.unit
    def test_multiple_exact(self):
        prs = [
            {"targetRefName": "refs/heads/master"},
            {"targetRefName": "refs/heads/QA"},
            {"targetRefName": "refs/heads/develop"},
        ]
        result = filter_prs_by_branches(prs, ["master", "QA"])
        assert len(result) == 2

    @pytest.mark.unit
    def test_wildcard_release_star(self):
        prs = [
            {"targetRefName": "refs/heads/release/v1.0"},
            {"targetRefName": "refs/heads/release/v2.0"},
            {"targetRefName": "refs/heads/master"},
            {"targetRefName": "refs/heads/QA"},
        ]
        result = filter_prs_by_branches(prs, ["release/*"])
        assert len(result) == 2

    @pytest.mark.unit
    def test_mixed_exact_and_wildcard(self):
        prs = [
            {"targetRefName": "refs/heads/master"},
            {"targetRefName": "refs/heads/release/v1.0"},
            {"targetRefName": "refs/heads/release/v2.0"},
            {"targetRefName": "refs/heads/develop"},
        ]
        result = filter_prs_by_branches(prs, ["master", "release/*"])
        assert len(result) == 3

    @pytest.mark.unit
    def test_no_match(self):
        prs = [
            {"targetRefName": "refs/heads/master"},
            {"targetRefName": "refs/heads/QA"},
        ]
        result = filter_prs_by_branches(prs, ["release/*"])
        assert len(result) == 0

    @pytest.mark.unit
    def test_empty_target_ref(self):
        prs = [
            {"targetRefName": ""},
            {"targetRefName": "refs/heads/release/v1.0"},
        ]
        result = filter_prs_by_branches(prs, ["release/*"])
        assert len(result) == 1

    @pytest.mark.unit
    def test_missing_target_ref(self):
        prs = [
            {"otherField": "value"},
            {"targetRefName": "refs/heads/release/v1.0"},
        ]
        result = filter_prs_by_branches(prs, ["release/*"])
        assert len(result) == 1

    @pytest.mark.unit
    def test_empty_branches_list(self):
        prs = [{"targetRefName": "refs/heads/master"}]
        result = filter_prs_by_branches(prs, [])
        assert len(result) == 1  # empty list = no filter


# ═══════════════════════════════════════════════════════════════════════════════
# search_release_definitions (mocked)
# ═══════════════════════════════════════════════════════════════════════════════
class TestSearchReleaseDefinitions:

    @pytest.mark.unit
    def test_search_returns_results(self):
        mock_data = {
            "value": [
                {"id": 1, "name": "my-repo-cd"},
                {"id": 2, "name": "my-repo-release"},
            ]
        }
        with patch("scm.azdo.azdo_pr_master_checker.api_get", return_value=mock_data):
            result = search_release_definitions("org", "proj", "my-repo", {})
        assert len(result) == 2

    @pytest.mark.unit
    def test_search_no_results(self):
        with patch("scm.azdo.azdo_pr_master_checker.api_get", return_value=None):
            result = search_release_definitions("org", "proj", "nonexistent", {})
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# search_cds_for_repos (mocked)
# ═══════════════════════════════════════════════════════════════════════════════
class TestSearchCdsForRepos:

    @pytest.mark.unit
    def test_search_multiple_repos(self):
        def mock_search(org, project, search_text, headers, debug=False):
            return [{"id": hash(search_text) % 1000, "name": f"{search_text}-cd"}]

        with patch("scm.azdo.azdo_pr_master_checker.search_release_definitions", side_effect=mock_search):
            result = search_cds_for_repos("org", "proj", ["repo-a", "repo-b"], {}, threads=2)
        assert "repo-a" in result
        assert "repo-b" in result

    @pytest.mark.unit
    def test_search_deduplicates(self):
        call_count = {"n": 0}

        def mock_search(org, project, search_text, headers, debug=False):
            call_count["n"] += 1
            # Same CD returned for different search terms
            return [{"id": 1, "name": "my-repo-cd"}]

        with patch("scm.azdo.azdo_pr_master_checker.search_release_definitions", side_effect=mock_search):
            result = search_cds_for_repos("org", "proj", ["my-repo"], {}, threads=1)
        # Should deduplicate: repo name search + parts
        assert "my-repo" in result


# ═══════════════════════════════════════════════════════════════════════════════
# normalize
# ═══════════════════════════════════════════════════════════════════════════════
class TestNormalize:

    @pytest.mark.unit
    def test_basic(self):
        assert normalize("My-Repo") == "myrepo"

    @pytest.mark.unit
    def test_underscores(self):
        assert normalize("my_repo_name") == "myreponame"

    @pytest.mark.unit
    def test_dots(self):
        assert normalize("my.repo") == "myrepo"

    @pytest.mark.unit
    def test_spaces(self):
        assert normalize("my repo") == "myrepo"

    @pytest.mark.unit
    def test_mixed(self):
        assert normalize("My-Repo_Name.v2") == "myreponamev2"


# ═══════════════════════════════════════════════════════════════════════════════
# find_cd_candidates_for_repo
# ═══════════════════════════════════════════════════════════════════════════════
class TestFindCdCandidatesForRepo:

    @pytest.mark.unit
    def test_exact_match(self):
        release_defs = [
            {"id": 1, "name": "my-repo"},
            {"id": 2, "name": "other-repo"},
        ]
        result = find_cd_candidates_for_repo("my-repo", release_defs)
        assert len(result) >= 1
        assert result[0][0] == 1  # cd_id
        assert result[0][1] == 100  # exact match score

    @pytest.mark.unit
    def test_prefix_match(self):
        release_defs = [
            {"id": 1, "name": "my-repo-cd"},
            {"id": 2, "name": "other-repo"},
        ]
        result = find_cd_candidates_for_repo("my-repo", release_defs)
        assert len(result) >= 1
        assert result[0][0] == 1
        assert result[0][1] == 90  # prefix match score

    @pytest.mark.unit
    def test_no_match(self):
        release_defs = [
            {"id": 1, "name": "completely-different"},
        ]
        result = find_cd_candidates_for_repo("my-repo", release_defs)
        assert len(result) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# find_cd_by_artifact_source
# ═══════════════════════════════════════════════════════════════════════════════
class TestFindCdByArtifactSource:

    @pytest.mark.unit
    def test_match_found(self):
        cd_details = {
            1: {
                "name": "my-repo-cd",
                "artifacts": [
                    {
                        "type": "Git",
                        "definitionReference": {
                            "definition": {"name": "my-repo"}
                        }
                    }
                ]
            }
        }
        result = find_cd_by_artifact_source("my-repo", cd_details)
        assert result is not None
        assert result["name"] == "my-repo-cd"

    @pytest.mark.unit
    def test_case_insensitive(self):
        cd_details = {
            1: {
                "name": "My-Repo-CD",
                "artifacts": [
                    {
                        "type": "Git",
                        "definitionReference": {
                            "definition": {"name": "My-Repo"}
                        }
                    }
                ]
            }
        }
        result = find_cd_by_artifact_source("my-repo", cd_details)
        assert result is not None

    @pytest.mark.unit
    def test_no_match(self):
        cd_details = {
            1: {
                "name": "other-cd",
                "artifacts": [
                    {
                        "type": "Git",
                        "definitionReference": {
                            "definition": {"name": "other-repo"}
                        }
                    }
                ]
            }
        }
        result = find_cd_by_artifact_source("my-repo", cd_details)
        assert result is None

    @pytest.mark.unit
    def test_none_cd_detail_skipped(self):
        cd_details = {1: None, 2: {"name": "cd2", "artifacts": []}}
        result = find_cd_by_artifact_source("my-repo", cd_details)
        assert result is None

    @pytest.mark.unit
    def test_empty_details_map(self):
        result = find_cd_by_artifact_source("my-repo", {})
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# find_cd_for_repo_with_details
# ═══════════════════════════════════════════════════════════════════════════════
class TestFindCdForRepoWithDetails:

    @pytest.mark.unit
    def test_artifact_source_priority(self):
        release_defs = [{"id": 1, "name": "my-repo-cd"}]
        cd_details = {
            1: {
                "name": "my-repo-cd",
                "artifacts": [
                    {
                        "type": "Git",
                        "definitionReference": {
                            "definition": {"name": "my-repo"}
                        }
                    }
                ]
            }
        }
        result = find_cd_for_repo_with_details("my-repo", release_defs, cd_details)
        assert result is not None
        assert result["name"] == "my-repo-cd"

    @pytest.mark.unit
    def test_fallback_by_name(self):
        release_defs = [{"id": 1, "name": "my-repo"}]
        cd_details = {1: {"name": "my-repo", "artifacts": []}}
        result = find_cd_for_repo_with_details("my-repo", release_defs, cd_details)
        assert result is not None

    @pytest.mark.unit
    def test_none_detail_in_map(self):
        release_defs = [{"id": 1, "name": "my-repo"}]
        cd_details = {1: None}
        result = find_cd_for_repo_with_details("my-repo", release_defs, cd_details)
        assert result is not None  # falls back to release_def summary


# ═══════════════════════════════════════════════════════════════════════════════
# has_stage
# ═══════════════════════════════════════════════════════════════════════════════
class TestHasStage:

    @pytest.mark.unit
    def test_stage_found(self):
        detail = {"environments": [{"name": "validador"}, {"name": "produccion"}]}
        assert has_stage(detail, "validador") is True

    @pytest.mark.unit
    def test_stage_not_found(self):
        detail = {"environments": [{"name": "produccion"}]}
        assert has_stage(detail, "validador") is False

    @pytest.mark.unit
    def test_case_insensitive(self):
        detail = {"environments": [{"name": "Validador"}]}
        assert has_stage(detail, "validador") is True

    @pytest.mark.unit
    def test_no_environments(self):
        detail = {"environments": []}
        assert has_stage(detail, "validador") is False

    @pytest.mark.unit
    def test_missing_environments_key(self):
        detail = {}
        assert has_stage(detail, "validador") is False
