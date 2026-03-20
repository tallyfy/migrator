"""
SurveyMonkey API Client
Handles interactions with SurveyMonkey API v3
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SurveyMonkeyClient:
    """Client for SurveyMonkey API v3"""

    def __init__(self, access_token: str):
        """Initialize SurveyMonkey client"""
        self.access_token = access_token
        self.base_url = "https://api.surveymonkey.com/v3"

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        })

        logger.info("SurveyMonkey client initialized")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make API request with error handling"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()

            if response.status_code == 204:
                return {'success': True}

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

    def _paginate(self, endpoint: str, params: Optional[Dict] = None,
                  max_pages: int = 100) -> List[Dict[str, Any]]:
        """Paginate through API results

        SurveyMonkey uses page/per_page pagination with links in response.
        """
        if params is None:
            params = {}

        params.setdefault('per_page', 100)
        params.setdefault('page', 1)

        all_items = []

        for _ in range(max_pages):
            response = self._make_request('GET', endpoint, params=params)

            items = response.get('data', [])
            all_items.extend(items)

            # Check for more pages
            links = response.get('links', {})
            if not links.get('next'):
                break

            params['page'] = params.get('page', 1) + 1

        return all_items

    # Surveys
    def get_surveys(self, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
        """Get all surveys with pagination"""
        params = {
            'page': page,
            'per_page': per_page,
            'sort_by': 'date_modified',
            'sort_order': 'DESC'
        }
        return self._make_request('GET', '/surveys', params=params)

    def get_all_surveys(self) -> List[Dict[str, Any]]:
        """Get all surveys across all pages"""
        return self._paginate('/surveys')

    def get_survey_details(self, survey_id: str) -> Dict[str, Any]:
        """Get full survey details including pages and questions"""
        return self._make_request('GET', f'/surveys/{survey_id}/details')

    def get_survey(self, survey_id: str) -> Dict[str, Any]:
        """Get basic survey info"""
        return self._make_request('GET', f'/surveys/{survey_id}')

    # Survey Responses
    def get_survey_responses(self, survey_id: str, page: int = 1,
                             per_page: int = 100, status: str = 'completed') -> Dict[str, Any]:
        """Get survey responses with pagination"""
        params = {
            'page': page,
            'per_page': per_page,
            'status': status,
            'sort_by': 'date_modified',
            'sort_order': 'DESC'
        }
        return self._make_request('GET', f'/surveys/{survey_id}/responses/bulk', params=params)

    def get_all_survey_responses(self, survey_id: str,
                                 status: str = 'completed') -> List[Dict[str, Any]]:
        """Get all responses for a survey across all pages"""
        return self._paginate(
            f'/surveys/{survey_id}/responses/bulk',
            params={'status': status}
        )

    def get_response_details(self, survey_id: str, response_id: str) -> Dict[str, Any]:
        """Get individual response details"""
        return self._make_request('GET', f'/surveys/{survey_id}/responses/{response_id}')

    # Collectors
    def get_collectors(self, survey_id: str) -> Dict[str, Any]:
        """Get collectors for a survey"""
        return self._make_request('GET', f'/surveys/{survey_id}/collectors')

    def get_collector_details(self, collector_id: str) -> Dict[str, Any]:
        """Get collector details"""
        return self._make_request('GET', f'/collectors/{collector_id}')

    # User/Account
    def get_me(self) -> Dict[str, Any]:
        """Get current user info"""
        return self._make_request('GET', '/users/me')

    def get_groups(self) -> Dict[str, Any]:
        """Get groups/teams"""
        return self._make_request('GET', '/groups')

    def get_group_members(self, group_id: str) -> Dict[str, Any]:
        """Get members of a group"""
        return self._make_request('GET', f'/groups/{group_id}/members')

    # Discovery
    def discover_account(self) -> Dict[str, Any]:
        """Discover complete account data"""
        discovery = {
            'timestamp': datetime.utcnow().isoformat(),
            'statistics': {},
            'surveys': []
        }

        # Get current user
        try:
            me = self.get_me()
            discovery['account'] = me
        except Exception as e:
            logger.warning(f"Could not fetch account info: {e}")

        # Get all surveys
        surveys_response = self.get_surveys()
        surveys = surveys_response.get('data', [])
        discovery['statistics']['total_surveys'] = len(surveys)

        # Get details for each survey (limited for discovery)
        total_questions = 0
        total_responses = 0

        for survey in surveys[:20]:  # Limit for discovery
            try:
                survey_details = self.get_survey_details(survey['id'])

                # Count questions across all pages
                question_count = 0
                for page in survey_details.get('pages', []):
                    question_count += len(page.get('questions', []))

                # Get response count
                responses = self.get_survey_responses(survey['id'], per_page=1)
                response_count = responses.get('total', 0)

                total_questions += question_count
                total_responses += response_count

                discovery['surveys'].append({
                    'id': survey['id'],
                    'title': survey.get('title'),
                    'questions': question_count,
                    'pages': len(survey_details.get('pages', [])),
                    'responses': response_count,
                    'date_created': survey.get('date_created'),
                    'date_modified': survey.get('date_modified')
                })
            except Exception as e:
                logger.warning(f"Could not fetch details for survey {survey['id']}: {e}")

        discovery['statistics']['total_questions'] = total_questions
        discovery['statistics']['total_responses'] = total_responses

        # Get groups
        try:
            groups = self.get_groups()
            discovery['statistics']['groups'] = len(groups.get('data', []))
        except Exception as e:
            logger.warning(f"Could not fetch groups: {e}")

        return discovery

    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            self.get_me()
            logger.info("SurveyMonkey API connection successful")
            return True
        except Exception as e:
            logger.error(f"SurveyMonkey API connection failed: {e}")
            return False
