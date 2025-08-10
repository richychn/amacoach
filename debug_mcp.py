#!/usr/bin/env python3
"""
Debug script for Claude.ai Remote MCP integration.
Run this alongside your MCP server to help troubleshoot issues.
"""

import requests
import json
import time
import sys

def test_mcp_endpoint(base_url):
    """Test the MCP server endpoints that Claude.ai uses."""
    
    print(f"🔍 Testing MCP Server at: {base_url}")
    print("=" * 60)
    
    # Test 1: Health check
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        if response.status_code != 200:
            print("   ❌ Health check failed")
            return False
        print("   ✅ Health check passed")
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False
    
    # Test 2: Client registration
    print("\n2. Testing client registration...")
    try:
        reg_data = {
            "client_name": "Claude.ai Debug Test",
            "grant_types": ["client_credentials"],
            "response_types": ["token"]
        }
        response = requests.post(f"{base_url}/register", json=reg_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        if response.status_code != 200:
            print("   ❌ Client registration failed")
            return False
        print("   ✅ Client registration passed")
    except Exception as e:
        print(f"   ❌ Client registration error: {e}")
        return False
    
    # Test 3: MCP initialization
    print("\n3. Testing MCP initialization...")
    try:
        init_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "Claude.ai", "version": "1.0"}
            }
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        response = requests.post(base_url, json=init_data, headers=headers)
        print(f"   Status: {response.status_code}")
        result = response.json()
        print(f"   Protocol Version: {result['result']['protocolVersion']}")
        print(f"   Server Name: {result['result']['serverInfo']['name']}")
        print(f"   Capabilities: {json.dumps(result['result']['capabilities'], indent=4)}")
        if response.status_code != 200:
            print("   ❌ MCP initialization failed")
            return False
        print("   ✅ MCP initialization passed")
    except Exception as e:
        print(f"   ❌ MCP initialization error: {e}")
        return False
    
    # Test 4: Tools list
    print("\n4. Testing tools list...")
    try:
        tools_data = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        response = requests.post(base_url, json=tools_data, headers=headers)
        print(f"   Status: {response.status_code}")
        result = response.json()
        tools = result['result']['tools']
        print(f"   Found {len(tools)} tools:")
        for tool in tools:
            name = tool['name']
            # Validate tool name pattern
            import re
            if re.match(r'^[a-zA-Z0-9_-]{1,64}$', name):
                print(f"   ✅ {name} (valid name)")
            else:
                print(f"   ❌ {name} (INVALID name - fails pattern ^[a-zA-Z0-9_-]{{1,64}}$)")
        if response.status_code != 200:
            print("   ❌ Tools list failed")
            return False
        print("   ✅ Tools list passed")
    except Exception as e:
        print(f"   ❌ Tools list error: {e}")
        return False
    
    # Test 5: Tool call
    print("\n5. Testing tool call...")
    try:
        call_data = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "generate_workout_guidance",
                "arguments": {"user_id": "debug_test"}
            }
        }
        response = requests.post(base_url, json=call_data, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            content = result['result']['content'][0]['text']
            print(f"   Content length: {len(content)} characters")
            print("   ✅ Tool call passed")
        else:
            print(f"   Response: {response.text}")
            print("   ❌ Tool call failed")
            return False
    except Exception as e:
        print(f"   ❌ Tool call error: {e}")
        return False
    
    # Test 6: SSE connection
    print("\n6. Testing SSE stream (GET request)...")
    try:
        headers_sse = {"Accept": "text/event-stream"}
        response = requests.get(base_url, headers=headers_sse, stream=True, timeout=3)
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        if response.status_code == 200:
            print("   ✅ SSE stream connection passed")
        else:
            print("   ❌ SSE stream connection failed")
    except requests.exceptions.ReadTimeout:
        print("   ✅ SSE stream timeout (expected for streaming connection)")
    except Exception as e:
        print(f"   ❌ SSE stream error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 All MCP server tests completed successfully!")
    print("\nIf Claude.ai Remote MCP still isn't working, the issue is likely:")
    print("1. Network connectivity between Claude.ai and your server")
    print("2. Claude.ai's MCP integration (known issues exist)")
    print("3. Firewall or security group blocking requests")
    print("4. Server not accessible from Claude.ai's infrastructure")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_mcp.py <server_url>")
        print("Example: python debug_mcp.py http://localhost:8000")
        print("Example: python debug_mcp.py https://your-railway-app.railway.app")
        sys.exit(1)
    
    server_url = sys.argv[1].rstrip('/')
    test_mcp_endpoint(server_url)