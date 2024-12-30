"""Authentication module for Home Assistant OAuth flow."""
import os
import json
import webbrowser
import socket
import secrets
import logging
from typing import Optional, Dict, Tuple
from urllib.parse import urlencode, urlparse
import aiohttp
import yaml

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Authentication related errors."""
    pass

class HomeAssistantAuth:
    """Handle Home Assistant OAuth authentication."""
    
    def __init__(self, ha_url: str):
        """Initialize the auth handler."""
        # Ensure URL has protocol
        if not ha_url.startswith(('http://', 'https://')):
            ha_url = f"http://{ha_url}"
        self.ha_url = ha_url.rstrip('/')
        self._config_dir = self._get_config_dir()
        
    def _get_config_dir(self) -> str:
        """Get the configuration directory for the current platform."""
        if os.name == 'nt':  # Windows
            config_dir = os.path.join(os.environ['APPDATA'], 'timewise-guardian')
        elif os.name == 'posix':  # Linux/macOS
            if os.path.exists('/Applications'):  # macOS
                config_dir = os.path.expanduser('~/Library/Application Support/timewise-guardian')
            else:  # Linux
                config_dir = os.path.expanduser('~/.config/timewise-guardian')
        else:
            raise RuntimeError(f"Unsupported platform: {os.name}")
        
        os.makedirs(config_dir, exist_ok=True)
        return config_dir
    
    def _create_local_server(self) -> Tuple[socket.socket, int]:
        """Create a local server for OAuth callback."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        return sock, port
    
    async def authenticate(self, computer_id: str, system_user: str) -> Dict[str, str]:
        """Perform OAuth authentication with Home Assistant."""
        # Generate state and code verifier
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        
        # Create local server for callback
        server_socket, port = self._create_local_server()
        redirect_uri = f"http://localhost:{port}"
        
        # Build authorization URL
        auth_params = {
            'client_id': 'timewise-guardian',
            'redirect_uri': redirect_uri,
            'state': state,
            'code_verifier': code_verifier,
            'response_type': 'code'
        }
        auth_url = f"{self.ha_url}/auth/authorize?{urlencode(auth_params)}"
        
        # Open browser for authentication
        print(f"\nOpening browser for Home Assistant authentication...")
        print("Note: You only need to authenticate once per computer. This grants the client access to Home Assistant.")
        webbrowser.open(auth_url)
        
        # Wait for callback
        print("Waiting for authentication...")
        client_socket, _ = server_socket.accept()
        response = client_socket.recv(4096).decode('utf-8')
        
        # Send success page
        success_page = """
        <html>
            <body style="text-align: center; font-family: Arial, sans-serif;">
                <h1>Authentication Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                <p>Note: The detected system user can be mapped to a Home Assistant user in the UI.</p>
            </body>
        </html>
        """
        client_socket.send(b'HTTP/1.1 200 OK\r\n')
        client_socket.send(b'Content-Type: text/html\r\n')
        client_socket.send(b'\r\n')
        client_socket.send(success_page.encode())
        client_socket.close()
        server_socket.close()
        
        # Extract authorization code
        code = None
        received_state = None
        for line in response.split('\n'):
            if line.startswith('GET'):
                query = line.split(' ')[1].split('?')[1]
                params = dict(param.split('=') for param in query.split('&'))
                code = params.get('code')
                received_state = params.get('state')
        
        if not code or received_state != state:
            raise AuthenticationError("Invalid response from Home Assistant")
        
        # Exchange code for token
        async with aiohttp.ClientSession() as session:
            token_url = f"{self.ha_url}/auth/token"
            token_data = {
                'grant_type': 'authorization_code',
                'code': code,
                'client_id': 'timewise-guardian',
                'code_verifier': code_verifier
            }
            
            async with session.post(token_url, data=token_data) as response:
                if response.status != 200:
                    raise AuthenticationError(f"Token exchange failed: {await response.text()}")
                token_response = await response.json()
        
        # Save configuration
        config = {
            'ha_url': self.ha_url,
            'ha_token': token_response['access_token'],
            'sync_interval': 30,
            'computer_id': computer_id,
            'system_user': system_user
        }
        
        config_path = os.path.join(self._config_dir, 'config.yaml')
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        print(f"\nConfiguration saved to: {config_path}")
        return config 