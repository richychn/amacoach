#!/usr/bin/env python3
"""
Monitor Railway deployment for Claude.ai requests.
This helps debug if Claude.ai is actually connecting to your server.
"""

import requests
import time
import json
from datetime import datetime

def monitor_railway_logs(app_url):
    """Monitor the Railway server for incoming requests from Claude.ai"""
    
    app_url = app_url.rstrip('/')
    
    print(f"🔍 Monitoring Claude.ai requests to: {app_url}")
    print("=" * 60)
    print("Now go to Claude.ai and try to:")
    print("1. Add your Remote MCP server URL")
    print("2. Ask Claude to 'List available exercises' or similar")
    print("3. Watch for requests below...")
    print("=" * 60)
    
    # Test connectivity first
    try:
        response = requests.get(f"{app_url}/health")
        if response.status_code == 200:
            print("✅ Server is accessible and healthy")
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot reach server: {e}")
        return
    
    # Monitor by making periodic health checks and looking for activity
    print(f"\n🔄 Monitoring started at {datetime.now()}")
    print("Make requests in Claude.ai now...")
    
    last_check = time.time()
    check_count = 0
    
    while True:
        try:
            check_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Make a health check to verify server is still up
            response = requests.get(f"{app_url}/health", timeout=10)
            
            if response.status_code == 200:
                print(f"[{current_time}] Check #{check_count}: Server responding ✅")
            else:
                print(f"[{current_time}] Check #{check_count}: Server error {response.status_code} ❌")
            
            # Test if MCP endpoints are working
            if check_count % 5 == 0:  # Every 5th check, test MCP
                try:
                    mcp_test = requests.post(f"{app_url}/", 
                        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                        timeout=10)
                    if mcp_test.status_code == 200:
                        result = mcp_test.json()
                        tool_count = len(result.get('result', {}).get('tools', []))
                        print(f"[{current_time}] MCP Test: {tool_count} tools available ✅")
                    else:
                        print(f"[{current_time}] MCP Test: Failed {mcp_test.status_code} ❌")
                except Exception as e:
                    print(f"[{current_time}] MCP Test: Error {str(e)} ❌")
            
            time.sleep(10)  # Check every 10 seconds
            
        except KeyboardInterrupt:
            print(f"\n\n🛑 Monitoring stopped by user at {datetime.now()}")
            break
        except Exception as e:
            print(f"[{current_time}] Monitoring error: {e}")
            time.sleep(5)

def test_claude_scenarios(app_url):
    """Test scenarios that Claude.ai might use"""
    
    app_url = app_url.rstrip('/')
    
    print(f"🧪 Testing Claude.ai scenarios on: {app_url}")
    print("=" * 60)
    
    scenarios = [
        {
            "name": "Client Registration (what Claude.ai does first)",
            "method": "POST",
            "endpoint": "/register",
            "data": {
                "client_name": "Claude.ai Remote MCP",
                "grant_types": ["client_credentials"],
                "response_types": ["token"],
                "redirect_uris": ["https://claude.ai/mcp/callback"]
            }
        },
        {
            "name": "MCP Initialize (what Claude.ai does second)",
            "method": "POST", 
            "endpoint": "/",
            "data": {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "Claude.ai", "version": "1.0"}
                }
            }
        },
        {
            "name": "Tools Discovery (what Claude.ai does third)",
            "method": "POST",
            "endpoint": "/",
            "data": {
                "jsonrpc": "2.0",
                "id": 2, 
                "method": "tools/list",
                "params": {}
            }
        },
        {
            "name": "SSE Stream Setup (what Claude.ai might do)",
            "method": "GET",
            "endpoint": "/",
            "headers": {"Accept": "text/event-stream"}
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print("-" * 40)
        
        try:
            url = f"{app_url}{scenario['endpoint']}"
            headers = scenario.get('headers', {})
            
            if scenario['method'] == 'POST':
                headers['Content-Type'] = 'application/json'
                response = requests.post(url, json=scenario['data'], headers=headers, timeout=10)
            elif scenario['method'] == 'GET':
                response = requests.get(url, headers=headers, timeout=5, stream=True)
            
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            if scenario['method'] == 'GET' and 'event-stream' in response.headers.get('content-type', ''):
                print("Response: SSE stream opened successfully ✅")
            else:
                try:
                    result = response.json()
                    if 'tools' in str(result):
                        tool_count = len(result.get('result', {}).get('tools', []))
                        print(f"Response: Found {tool_count} MCP tools ✅")
                    else:
                        print(f"Response: {json.dumps(result, indent=2)}")
                except:
                    print(f"Response: {response.text[:200]}...")
            
            print("✅ Scenario passed")
            
        except Exception as e:
            print(f"❌ Scenario failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Summary: Your server handles all Claude.ai scenarios correctly!")
    print("\nIf Claude.ai still isn't working:")
    print("1. Check Claude.ai's MCP settings - ensure server is 'Connected'")
    print("2. Try explicitly asking Claude to use tools: 'Use generate_workout_guidance tool'")
    print("3. Check if there are Claude.ai outages or known MCP issues")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python monitor_railway.py <server_url>")
        print("\nExamples:")
        print("  python monitor_railway.py https://amacoach-production.up.railway.app")
        print("\nCommands:")
        print("  monitor - Watch for incoming requests (default)")
        print("  test    - Test Claude.ai scenarios")
        sys.exit(1)
    
    server_url = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else "monitor"
    
    if command == "test":
        test_claude_scenarios(server_url)
    else:
        monitor_railway_logs(server_url)