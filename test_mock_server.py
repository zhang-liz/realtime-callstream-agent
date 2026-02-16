#!/usr/bin/env python3
"""
Mock server test to validate basic FastAPI functionality without external dependencies
"""

import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Mock config used when instantiating STT/LLM/TTS (they take api_key, config)
def _mock_config():
    c = MagicMock()
    c.silence_threshold_ms = 1500
    c.stt_sample_rate = 8000
    c.silence_threshold_db = -40.0
    c.llm_model = "gpt-3.5-turbo"
    c.llm_max_tokens = 150
    c.llm_temperature = 0.7
    c.elevenlabs_voice_id = "21m00Tcm4TlvDq8ikWAM"
    c.tts_chunk_size = 320
    return c


def test_mock_imports():
    """Test that we can mock the problematic imports and instantiate STT/LLM/TTS with (api_key, config)."""
    mock_modules = [
        'twilio.twiml.voice_response',
        'twilio.request_validator',
        'openai',
        'elevenlabs',
        'pydub',
        'structlog'
    ]
    for module in mock_modules:
        sys.modules[module] = Mock()

    from stt import StreamingSTT
    from llm import CollectionsAgent
    from tts import ElevenLabsTTS, TwilioAudioStreamer

    mock_cfg = _mock_config()
    stt = StreamingSTT("mock-key", mock_cfg)
    llm = CollectionsAgent("mock-key", mock_cfg)
    tts = ElevenLabsTTS("mock-key", mock_cfg)

    assert stt is not None
    assert llm is not None
    assert tts is not None

def test_app_mock():
    """Test that the FastAPI app can be created with mocks (config and state manager)."""
    mock_config = _mock_config()
    mock_config.twilio_auth_token = "mock-token"
    mock_config.openai_api_key = "mock-key"
    mock_config.elevenlabs_api_key = "mock-key"
    mock_config.public_host = "localhost:8000"

    with patch.dict('sys.modules', {
        'twilio.twiml.voice_response': Mock(),
        'twilio.request_validator': Mock(),
        'structlog': Mock(),
    }):
        with patch('config.Config.from_env', return_value=mock_config), \
             patch('stt.StreamingSTT'), \
             patch('llm.CollectionsAgent'), \
             patch('tts.ElevenLabsTTS'), \
             patch('tts.TwilioAudioStreamer'), \
             patch('state.CallStateManager'):
            if 'app' in sys.modules:
                del sys.modules['app']
            import app

            assert hasattr(app, 'app')
            assert app.app.title == "Voice Agent"
            assert hasattr(app, 'config')
            assert app.config is mock_config

def test_websocket_handler_logic():
    """Test that WebSocket handler functions exist in the handlers module."""
    from handlers import handle_start, handle_media, handle_stop, handle_mark

    assert callable(handle_start)
    assert callable(handle_media)
    assert callable(handle_stop)
    assert callable(handle_mark)

def test_environment_setup():
    """Test that app starts with config loaded (via mocked Config.from_env)."""
    mock_config = _mock_config()
    mock_config.twilio_auth_token = "mock-token"
    mock_config.openai_api_key = "mock-key"
    mock_config.elevenlabs_api_key = "mock-key"
    mock_config.public_host = "localhost:8000"

    with patch.dict('sys.modules', {
        'twilio.twiml.voice_response': Mock(),
        'twilio.request_validator': Mock(),
        'structlog': Mock(),
    }):
        with patch('config.Config.from_env', return_value=mock_config), \
             patch('stt.StreamingSTT'), \
             patch('llm.CollectionsAgent'), \
             patch('tts.ElevenLabsTTS'), \
             patch('tts.TwilioAudioStreamer'), \
             patch('state.CallStateManager'):
            if 'app' in sys.modules:
                del sys.modules['app']
            import app

            assert hasattr(app, 'config')
            assert app.config.twilio_auth_token == "mock-token"
            assert app.config.openai_api_key == "mock-key"
            assert app.config.elevenlabs_api_key == "mock-key"

def test_frontend_build_check():
    """Check frontend config files exist and have expected structure."""
    import json

    with open("voice-agent-ui/package.json", 'r') as f:
        package = json.load(f)
    assert "name" in package and "dependencies" in package

    with open("voice-agent-ui/next.config.js", 'r') as f:
        next_config = f.read()
    assert "content" in next_config or "experimental" in next_config or "module" in next_config

    with open("voice-agent-ui/tsconfig.json", 'r') as f:
        ts_config = json.load(f)
    assert "compilerOptions" in ts_config

    with open("voice-agent-ui/tailwind.config.js", 'r') as f:
        tailwind_config = f.read()
    assert "content" in tailwind_config
    assert "theme" in tailwind_config

def run_mock_tests():
    """Run all mock tests (when executed as script)."""
    print("🧪 Running Mock Server Tests (No External Dependencies)")
    print("=" * 60)

    tests = [
        test_mock_imports,
        test_app_mock,
        test_websocket_handler_logic,
        test_environment_setup,
        test_frontend_build_check,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")

    print("\n" + "=" * 60)
    print(f"📊 Mock Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All mock tests passed!")
        return True
    print("⚠️  Some mock tests failed. Check the issues above.")
    return False

if __name__ == "__main__":
    success = run_mock_tests()
    sys.exit(0 if success else 1)
