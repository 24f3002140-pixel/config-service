from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os
import yaml
from dotenv import load_dotenv
import uvicorn

app = FastAPI()

# Enable CORS (allows browser to access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConfigResponse(BaseModel):
    port: int
    workers: int
    debug: bool
    log_level: str
    api_key: str

def load_config():
    """Load configuration from all layers with proper precedence."""
    
    # Layer 1: Defaults (lowest precedence)
    config = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000"
    }
    
    # Layer 2: YAML file
    try:
        with open('config.development.yaml', 'r') as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config:
                if 'port' in yaml_config:
                    config['port'] = int(yaml_config['port'])
                if 'workers' in yaml_config:
                    config['workers'] = int(yaml_config['workers'])
                if 'debug' in yaml_config:
                    config['debug'] = str(yaml_config['debug']).lower() in ['true', '1', 'yes', 'on']
                if 'log_level' in yaml_config:
                    config['log_level'] = str(yaml_config['log_level'])
                if 'api_key' in yaml_config:
                    config['api_key'] = str(yaml_config['api_key'])
    except FileNotFoundError:
        pass
    
    # Layer 3: .env file
    load_dotenv()
    if os.getenv('NUM_WORKERS'):
        config['workers'] = int(os.getenv('NUM_WORKERS'))
    if os.getenv('APP_DEBUG'):
        config['debug'] = str(os.getenv('APP_DEBUG')).lower() in ['true', '1', 'yes', 'on']
    
    # Layer 4: OS environment variables (highest among config files)
    app_port = os.getenv('APP_PORT')
    if app_port:
        config['port'] = int(app_port)
    
    app_workers = os.getenv('APP_WORKERS')
    if app_workers:
        config['workers'] = int(app_workers)
    
    app_debug = os.getenv('APP_DEBUG')
    if app_debug is not None:
        config['debug'] = str(app_debug).lower() in ['true', '1', 'yes', 'on']
    
    app_log_level = os.getenv('APP_LOG_LEVEL')
    if app_log_level:
        config['log_level'] = str(app_log_level)
    
    app_api_key = os.getenv('APP_API_KEY')
    if app_api_key:
        config['api_key'] = str(app_api_key)
    
    return config

def apply_cli_overrides(config: Dict[str, Any], overrides: Optional[List[str]] = Query(None)):
    """Apply CLI overrides from query parameters with highest precedence."""
    if not overrides:
        return config
    
    for override in overrides:
        if '=' not in override:
            continue
        
        key, value = override.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        # Type coercion
        if key in ['port', 'workers']:
            config[key] = int(value)
        elif key == 'debug':
            config[key] = value.lower() in ['true', '1', 'yes', 'on']
        elif key == 'log_level':
            config[key] = value
        elif key == 'api_key':
            config[key] = value
        elif key == 'NUM_WORKERS':
            config['workers'] = int(value)
    
    return config

@app.get("/effective-config", response_model=ConfigResponse)
async def get_effective_config(set: Optional[List[str]] = Query(None)):
    """Get effective configuration."""
    config = load_config()
    config = apply_cli_overrides(config, set)
    config['api_key'] = "****"  # Mask api_key
    return config

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)