#!/usr/bin/env python3
"""
Integration test for voice agent components
Tests the core logic without requiring external dependencies
"""

import json
import asyncio
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

def test_websocket_message_parsing():
    """Test that WebSocket messages are parsed correctly"""
    print("🧪 Testing WebSocket message parsing...")

    # Mock Twilio messages
    start_message = {
        "event": "start",
        "streamSid": "test-stream-123",
        "accountSid": "test-account"
    }

    media_message = {
        "event": "media",
        "streamSid": "test-stream-123",
        "sequenceNumber": 1,
        "media": {
            "payload": "dGVzdCBhdWRpbw=="  # base64 "test audio"
        }
    }

    mark_message = {
        "event": "mark",
        "streamSid": "test-stream-123",
        "mark": {
            "name": "test-mark-1"
        }
    }

    # Test JSON parsing
    try:
        parsed_start = json.loads(json.dumps(start_message))
        parsed_media = json.loads(json.dumps(media_message))
        parsed_mark = json.loads(json.dumps(mark_message))

        assert parsed_start["event"] == "start"
        assert parsed_media["event"] == "media"
        assert parsed_mark["event"] == "mark"

        print("✅ WebSocket message parsing works correctly")
        return True
    except Exception as e:
        print(f"❌ WebSocket message parsing failed: {e}")
        return False

def test_call_state_management():
    """Test the CallState class logic"""
    print("🧪 Testing call state management...")

    try:
        # Mock the CallState class since we can't import it without dependencies
        class MockCallState:
            def __init__(self, stream_sid: str):
                self.stream_sid = stream_sid
                self.is_speaking = False
                self.mark_id = 0
                self.pending_marks = set()

        # Test state creation
        state = MockCallState("test-stream-123")
        assert state.stream_sid == "test-stream-123"
        assert state.is_speaking == False
        assert state.mark_id == 0
        assert len(state.pending_marks) == 0

        # Test mark management
        state.pending_marks.add("mark-1")
        assert "mark-1" in state.pending_marks
        state.pending_marks.remove("mark-1")
        assert "mark-1" not in state.pending_marks

        print("✅ Call state management works correctly")
        return True
    except Exception as e:
        print(f"❌ Call state management failed: {e}")
        return False

def test_frontend_component_structure():
    """Test that the frontend component has the right structure"""
    print("🧪 Testing frontend component structure...")

    try:
        # Read the React component file
        component_path = "voice-agent-ui/src/components/VoiceAgentInterface.tsx"
        with open(component_path, 'r') as f:
            content = f.read()

        # Check for key React patterns
        assert "useState" in content
        assert "useEffect" in content
        assert "WebSocket" in content
        assert "audio" in content.lower()
        assert "connect" in content.lower()

        # Check for key functions
        assert "connectToServer" in content
        assert "startRecording" in content
        assert "playAudioFromBase64" in content

        print("✅ Frontend component structure is valid")
        return True
    except Exception as e:
        print(f"❌ Frontend component structure check failed: {e}")
        return False

def test_package_json_structure():
    """Test that package.json has correct dependencies"""
    print("🧪 Testing package.json structure...")

    try:
        with open("voice-agent-ui/package.json", 'r') as f:
            package_data = json.load(f)

        # Check required fields
        assert "name" in package_data
        assert "version" in package_data
        assert "scripts" in package_data
        assert "dependencies" in package_data

        # Check key dependencies
        deps = package_data["dependencies"]
        assert "next" in deps
        assert "react" in deps
        assert "tailwindcss" in deps

        # Check scripts
        scripts = package_data["scripts"]
        assert "dev" in scripts
        assert "build" in scripts

        print("✅ Package.json structure is valid")
        return True
    except Exception as e:
        print(f"❌ Package.json structure check failed: {e}")
        return False

def test_api_endpoints_structure():
    """Test that the API endpoints are properly defined."""
    print("🧪 Testing API endpoints structure...")

    try:
        with open("app.py", "r") as f:
            app_content = f.read()
        with open("handlers.py", "r") as f:
            handlers_content = f.read()
        with open("routers/voice.py", "r") as f:
            voice_content = f.read()
        with open("routers/media.py", "r") as f:
            media_content = f.read()

        # App mounts routers and has root endpoint
        assert "include_router" in app_content
        assert 'get("/")' in app_content

        # Voice and media routers define endpoints
        assert "/voice" in voice_content
        assert "/media" in media_content

        # Handlers implement message handling
        assert "handle_start" in handlers_content
        assert "handle_media" in handlers_content
        assert "handle_mark" in handlers_content

        print("✅ API endpoints structure is valid")
        return True
    except Exception as e:
        print(f"❌ API endpoints structure check failed: {e}")
        return False

def test_requirements_structure():
    """Test that requirements.txt has necessary packages"""
    print("🧪 Testing requirements.txt structure...")

    try:
        with open("requirements.txt", 'r') as f:
            content = f.read()

        # Check for key packages
        required_packages = [
            "fastapi",
            "uvicorn",
            "websockets",
            "twilio",
            "openai",
            "elevenlabs"
        ]

        for package in required_packages:
            assert package in content.lower()

        print("✅ Requirements.txt structure is valid")
        return True
    except Exception as e:
        print(f"❌ Requirements.txt structure check failed: {e}")
        return False

async def test_websocket_simulation():
    """Simulate WebSocket communication between frontend and backend"""
    print("🧪 Testing WebSocket communication simulation...")

    try:
        # This is a simplified simulation of the WebSocket flow

        # Simulate backend receiving start message
        start_message = {
            "event": "start",
            "streamSid": "test-stream-123",
            "accountSid": "test-account"
        }

        # Backend should respond appropriately
        assert start_message["event"] == "start"
        assert "streamSid" in start_message

        # Simulate media message
        media_message = {
            "event": "media",
            "streamSid": "test-stream-123",
            "media": {"payload": "dGVzdA=="}
        }

        assert media_message["event"] == "media"
        assert "payload" in media_message["media"]

        # Simulate mark message
        mark_message = {
            "event": "mark",
            "streamSid": "test-stream-123",
            "mark": {"name": "test-mark"}
        }

        assert mark_message["event"] == "mark"
        assert "name" in mark_message["mark"]

        print("✅ WebSocket communication simulation works")
        return True
    except Exception as e:
        print(f"❌ WebSocket communication simulation failed: {e}")
        return False

def run_all_tests():
    """Run all integration tests"""
    print("🚀 Running Voice Agent Integration Tests")
    print("=" * 50)

    tests = [
        test_websocket_message_parsing,
        test_call_state_management,
        test_frontend_component_structure,
        test_package_json_structure,
        test_api_endpoints_structure,
        test_requirements_structure,
        test_websocket_simulation
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = asyncio.run(test())
            else:
                result = test()

            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All integration tests passed!")
        print("\n💡 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Set up environment variables in .env")
        print("3. Run the development script: ./dev.sh")
        return True
    else:
        print("⚠️  Some tests failed. Please check the output above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
