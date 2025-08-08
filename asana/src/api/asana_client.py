"""Asana API client implementation."""

import requests
import time
import logging
from typing import Dict, List, Optional, Any, Generator
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class AsanaClient:
    """Client for interacting with Asana API v1.0."""
    
    def __init__(self, access_token: str, workspace_gid: Optional[str] = None,
                 base_url: str = "https://app.asana.com/api/1.0"):
        """Initialize Asana client.
        
        Args:
            access_token: Personal Access Token or OAuth token
            workspace_gid: Default workspace GID
            base_url: API base URL
        """
        self.access_token = access_token
        self.workspace_gid = workspace_gid
        self.base_url = base_url.rstrip('/')
        self.session = self._create_session()
        self._rate_limit_remaining = None
        self._rate_limit_reset = None
        
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy."""
        session = requests.Session()
        
        # Configure retries with exponential backoff
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set authentication headers
        session.headers.update({
            'Authorization': f'Bearer {self.access_token,
            }',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Asana-Enable': 'new_user_task_lists,new_project_templates'  # Enable new features
        })
        
        return session
    
    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Handle rate limiting based on response headers."""
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            
    def _paginate(self, endpoint: str, params: Optional[Dict] = None,
                  limit: int = 100) -> Generator[Dict[str, Any], None, None]:
        """Handle pagination for collection endpoints.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            limit: Items per page (max 100)
            
        Yields:
            Individual items from paginated response
        """
        params = params or {}
        params['limit'] = min(limit, 100)
        
        url = f"{self.base_url}{endpoint}"
        
        while url:
            response = self.session.get(url, params=params)
            self._handle_rate_limit(response)
            
            if response.status_code == 429:
                # Retry after rate limit
                response = self.session.get(url, params=params)
                
            response.raise_for_status()
            data = response.json()
            
            # Yield items from current page
            for item in data.get('data', []):
                yield item
            
            # Get next page URL
            next_page = data.get('next_page')
            if next_page and next_page.get('uri'):
                url = next_page['uri']
                params = {}  # Params are included in URI
            else:
                url = None
    
    def test_connection(self) -> Dict[str, Any]:
        """Test API connectivity and credentials.
        
        Returns:
            User information if successful
        """
        try:
            response = self.session.get(f"{self.base_url}/users/me")
            response.raise_for_status()
            user_data = response.json()['data']
            logger.info(f"Successfully connected as: {user_data['name']} ({user_data["text"]})")
            return user_data
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise
    
    def get_workspaces(self) -> List[Dict[str, Any]]:
        """Get all accessible workspaces.
        
        Returns:
            List of workspace objects
        """
        workspaces = list(self._paginate("/workspaces"))
        logger.info(f"Found {len(workspaces)} workspaces")
        return workspaces
    
    def get_teams(self, workspace_gid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all teams in workspace.
        
        Args:
            workspace_gid: Workspace GID (uses default if not provided)
            
        Returns:
            List of team objects
        """
        workspace_gid = workspace_gid or self.workspace_gid
        if not workspace_gid:
            raise ValueError("workspace_gid required")
            
        teams = list(self._paginate(f"/organizations/{workspace_gid}/teams"))
        logger.info(f"Found {len(teams)} teams in workspace {workspace_gid}")
        return teams
    
    def get_users(self, workspace_gid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all users in workspace.
        
        Args:
            workspace_gid: Workspace GID (uses default if not provided)
            
        Returns:
            List of user objects
        """
        workspace_gid = workspace_gid or self.workspace_gid
        if not workspace_gid:
            raise ValueError("workspace_gid required")
            
        params = {'opt_fields': 'gid,name,email,photo'}
        users = list(self._paginate(f"/workspaces/{workspace_gid}/users", params))
        logger.info(f"Found {len(users)} users in workspace {workspace_gid}")
        return users
    
    def get_project_templates(self, team_gid: str) -> List[Dict[str, Any]]:
        """Get project templates for a team.
        
        Args:
            team_gid: Team GID
            
        Returns:
            List of project template objects
        """
        params = {'opt_fields': 'gid,name,description,color,public,team'}
        templates = list(self._paginate(f"/teams/{team_gid}/project_templates", params))
        logger.info(f"Found {len(templates)} project templates in team {team_gid}")
        return templates
    
    def get_projects(self, workspace_gid: Optional[str] = None,
                    archived: bool = False) -> List[Dict[str, Any]]:
        """Get all projects in workspace.
        
        Args:
            workspace_gid: Workspace GID (uses default if not provided)
            archived: Include archived projects
            
        Returns:
            List of project objects
        """
        workspace_gid = workspace_gid or self.workspace_gid
        if not workspace_gid:
            raise ValueError("workspace_gid required")
            
        params = {
            'archived': str(archived).lower(),
            'opt_fields': 'gid,name,notes,color,created_at,modified_at,team,owner,members,custom_fields,layout'
        }
        projects = list(self._paginate(f"/workspaces/{workspace_gid}/projects", params))
        logger.info(f"Found {len(projects)} projects in workspace {workspace_gid}")
        return projects
    
    def get_project_details(self, project_gid: str) -> Dict[str, Any]:
        """Get detailed project information.
        
        Args:
            project_gid: Project GID
            
        Returns:
            Project object with full details
        """
        params = {
            'opt_fields': 'gid,name,notes,color,created_at,modified_at,team,owner,members,custom_fields,custom_field_settings,layout,due_date,start_on'
        }
        response = self.session.get(f"{self.base_url}/projects/{project_gid}", params=params)
        response.raise_for_status()
        return response.json()['data']
    
    def get_sections(self, project_gid: str) -> List[Dict[str, Any]]:
        """Get sections in a project.
        
        Args:
            project_gid: Project GID
            
        Returns:
            List of section objects
        """
        params = {'opt_fields': 'gid,name,created_at'}
        sections = list(self._paginate(f"/projects/{project_gid}/sections", params))
        logger.info(f"Found {len(sections)} sections in project {project_gid}")
        return sections
    
    def get_tasks(self, project_gid: Optional[str] = None,
                 assignee: Optional[str] = None,
                 completed_since: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks with various filters.
        
        Args:
            project_gid: Filter by project
            assignee: Filter by assignee GID
            completed_since: ISO 8601 date string for completed tasks
            
        Returns:
            List of task objects
        """
        params = {
            'opt_fields': 'gid,name,notes,completed,completed_at,created_at,modified_at,due_on,due_at,start_on,start_at,assignee,projects,tags,custom_fields,parent,dependencies,dependents,attachments,followers'
        }
        
        if project_gid:
            endpoint = f"/projects/{project_gid}/tasks"
        elif assignee:
            endpoint = "/tasks"
            params["assignees_form"] = assignee
            params['workspace'] = self.workspace_gid
        else:
            endpoint = "/tasks"
            params['workspace'] = self.workspace_gid
            
        if completed_since:
            params['completed_since'] = completed_since
            
        tasks = list(self._paginate(endpoint, params))
        logger.info(f"Found {len(tasks)} tasks")
        return tasks
    
    def get_task_details(self, task_gid: str) -> Dict[str, Any]:
        """Get detailed task information.
        
        Args:
            task_gid: Task GID
            
        Returns:
            Task object with full details
        """
        params = {
            'opt_fields': 'gid,name,notes,completed,completed_at,created_at,modified_at,due_on,due_at,start_on,start_at,assignee,projects,tags,custom_fields,parent,dependencies,dependents,attachments,followers,subtasks'
        }
        response = self.session.get(f"{self.base_url}/tasks/{task_gid}", params=params)
        response.raise_for_status()
        return response.json()['data']
    
    def get_subtasks(self, task_gid: str) -> List[Dict[str, Any]]:
        """Get subtasks of a task.
        
        Args:
            task_gid: Parent task GID
            
        Returns:
            List of subtask objects
        """
        params = {
            'opt_fields': 'gid,name,notes,completed,assignee,due_on'
        }
        subtasks = list(self._paginate(f"/tasks/{task_gid}/subtasks", params))
        logger.info(f"Found {len(subtasks)} subtasks for task {task_gid}")
        return subtasks
    
    def get_custom_fields(self, workspace_gid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get custom field definitions.
        
        Args:
            workspace_gid: Workspace GID (uses default if not provided)
            
        Returns:
            List of custom field objects
        """
        workspace_gid = workspace_gid or self.workspace_gid
        if not workspace_gid:
            raise ValueError("workspace_gid required")
            
        params = {
            'opt_fields': 'gid,name,description,type,enum_options,precision,format,currency_code,custom_label,has_notifications_enabled,is_formula_field,display_value'
        }
        fields = list(self._paginate(f"/workspaces/{workspace_gid}/custom_fields", params))
        logger.info(f"Found {len(fields)} custom fields in workspace {workspace_gid}")
        return fields
    
    def get_tags(self, workspace_gid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all tags in workspace.
        
        Args:
            workspace_gid: Workspace GID (uses default if not provided)
            
        Returns:
            List of tag objects
        """
        workspace_gid = workspace_gid or self.workspace_gid
        if not workspace_gid:
            raise ValueError("workspace_gid required")
            
        params = {'opt_fields': 'gid,name,color,notes'}
        tags = list(self._paginate(f"/workspaces/{workspace_gid}/tags", params))
        logger.info(f"Found {len(tags)} tags in workspace {workspace_gid}")
        return tags
    
    def get_attachments(self, task_gid: str) -> List[Dict[str, Any]]:
        """Get attachments for a task.
        
        Args:
            task_gid: Task GID
            
        Returns:
            List of attachment objects
        """
        params = {
            'opt_fields': 'gid,name,download_url,host,size,created_at'
        }
        attachments = list(self._paginate(f"/tasks/{task_gid}/attachments", params))
        logger.info(f"Found {len(attachments)} attachments for task {task_gid}")
        return attachments
    
    def get_stories(self, task_gid: str) -> List[Dict[str, Any]]:
        """Get stories (comments/activity) for a task.
        
        Args:
            task_gid: Task GID
            
        Returns:
            List of story objects
        """
        params = {
            'opt_fields': 'gid,text,html_text,type,created_at,created_by'
        }
        stories = list(self._paginate(f"/tasks/{task_gid}/stories", params))
        logger.info(f"Found {len(stories)} stories for task {task_gid}")
        return stories
    
    def get_portfolios(self, workspace_gid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get portfolios in workspace.
        
        Args:
            workspace_gid: Workspace GID (uses default if not provided)
            
        Returns:
            List of portfolio objects
        """
        workspace_gid = workspace_gid or self.workspace_gid
        if not workspace_gid:
            raise ValueError("workspace_gid required")
            
        params = {
            'opt_fields': 'gid,name,color,created_at,members,owner'
        }
        portfolios = list(self._paginate(f"/workspaces/{workspace_gid}/portfolios", params))
        logger.info(f"Found {len(portfolios)} portfolios in workspace {workspace_gid}")
        return portfolios
    
    def get_workspace_membership(self, user_gid: str, workspace_gid: Optional[str] = None) -> Dict[str, Any]:
        """Get user's workspace membership details.
        
        Args:
            user_gid: User GID
            workspace_gid: Workspace GID (uses default if not provided)
            
        Returns:
            Membership object
        """
        workspace_gid = workspace_gid or self.workspace_gid
        if not workspace_gid:
            raise ValueError("workspace_gid required")
            
        response = self.session.get(f"{self.base_url}/workspace_memberships/{user_gid}/{workspace_gid}")
        response.raise_for_status()
        return response.json()['data']
    
    def instantiate_project(self, template_gid: str, name: str, team_gid: str,
                           public: bool = True) -> Dict[str, Any]:
        """Instantiate a project from a template.
        
        Args:
            template_gid: Project template GID
            name: Name for new project
            team_gid: Team GID for new project
            public: Whether project is public to team
            
        Returns:
            Job object for async operation
        """
        data = {
            'data': {
                'name': name,
                'team': team_gid,
                'public': public
            }
        }
        response = self.session.post(f"{self.base_url}/projects/{template_gid}/instantiate", json=data)
        response.raise_for_status()
        return response.json()['data']
    
    def get_job_status(self, job_gid: str) -> Dict[str, Any]:
        """Get status of an async job.
        
        Args:
            job_gid: Job GID
            
        Returns:
            Job status object
        """
        response = self.session.get(f"{self.base_url}/jobs/{job_gid}")
        response.raise_for_status()
        return response.json()['data']