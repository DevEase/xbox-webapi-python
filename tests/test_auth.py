import os
import pytest
from betamax import Betamax

from xbox.webapi.authentication.manager import AuthenticationManager
from xbox.webapi.common.exceptions import AuthenticationException
from xbox.webapi.authentication.token import AccessToken, RefreshToken, XSTSToken
from xbox.webapi.common.userinfo import XboxLiveUserInfo


def test_extract_js_node(windows_live_authenticate_response):
    auth_manager = AuthenticationManager()
    js_node = auth_manager.extract_js_object(windows_live_authenticate_response, 'ServerData')

    assert js_node is not None
    assert js_node['sFTTag'] == "<input name=\"PPFT\" value=\"normally_base64_encoded_string_here+\"/>"
    assert js_node['urlPost'] == "https://login.live.com/ppsecure/post.srf?response_type=token"


def test_auth_invalid_credentials():
    auth_manager = AuthenticationManager()
    auth_manager.email_address = "invalid@mail.com"
    auth_manager.password = "abc123"

    with Betamax(auth_manager.session).use_cassette('invalid_auth'):
        with pytest.raises(AuthenticationException):
            auth_manager.authenticate()

    assert auth_manager.is_authenticated is False


def test_auth_valid_credentials():
    auth_manager = AuthenticationManager()
    auth_manager.email_address = "pyxb-testing@outlook.com"
    auth_manager.password = "password"

    with Betamax(auth_manager.session).use_cassette('full_auth'):
        auth_manager.authenticate(do_refresh=False)

    assert auth_manager.is_authenticated is True
    assert auth_manager.xsts_token.is_valid is True
    assert auth_manager.access_token.is_valid is True
    assert auth_manager.refresh_token.is_valid is True
    assert auth_manager.user_token.is_valid is True
    assert auth_manager.userinfo.userhash == '1674471606081042789'
    assert auth_manager.userinfo.xuid == '2535428504476914'
    assert auth_manager.userinfo.gamertag == 'xboxWebapiGamertag'


def test_auth_refresh_token():
    auth_manager = AuthenticationManager()
    auth_manager.refresh_token = RefreshToken(
        "CuZ*4TX7!SAF33cW*kzdFmgCLPRcz0DtUHFqjQgF726!FG3ScC5yMiDLsJYJ03m4fURrzf3J7X8l6A8mJGhHoRf42aHeJLrtp6wS"
        "Jh*PudaQdPNGJZHD1CpU4diJJxz0zhrijFsaAYXMqf3mSU7EerR5RtdHOwbcrlRlj7TBQ9RdLqWpy9KWsNhyPrwOMDJnBfAf3xsZ"
        "3g3QkmMeKGil85*q*MV*YqMPZTa8UVLPfM!jJeHwOjVhWPaYVq4hf6zIAwSLJl1Reo6GbkkPktrK3laFBGeqSkq651YgdjwtepwC"
        "Ef7oMwzz8c8msv8l95RU*QmtIjdRFd!fYtQctiGLDGs$"
    )

    with Betamax(auth_manager.session).use_cassette('token_refresh'):
        auth_manager.authenticate(do_refresh=True)

    assert auth_manager.is_authenticated is True
    assert auth_manager.xsts_token.is_valid is True
    assert auth_manager.access_token.is_valid is True
    assert auth_manager.refresh_token.is_valid is True
    assert auth_manager.user_token.is_valid is True
    assert auth_manager.userinfo.userhash == '1674471606081042789'
    assert auth_manager.userinfo.xuid == '2535428504476914'
    assert auth_manager.userinfo.gamertag == 'xboxWebapiGamertag'


def test_load_tokens_from_file(tokens_filepath):
    auth_manager = AuthenticationManager.from_file(tokens_filepath)

    assert auth_manager.userinfo is not None
    assert auth_manager.userinfo.userhash == '1674471606081042789'
    assert auth_manager.userinfo.xuid == '2535428504476914'
    assert auth_manager.userinfo.gamertag == 'xboxWebapiGamertag'

    assert auth_manager.access_token.is_valid is False
    assert auth_manager.refresh_token.is_valid is True
    assert auth_manager.user_token.is_valid is True
    assert auth_manager.xsts_token is None


def test_save_tokens_to_file(tmpdir, jwt, token_timestring):
    filepath = os.path.join(str(tmpdir), 'save_tokens.json')
    auth_manager = AuthenticationManager()

    auth_manager.access_token = AccessToken(jwt, 1000)
    auth_manager.xsts_token = XSTSToken(jwt, token_timestring, token_timestring)
    auth_manager.userinfo = XboxLiveUserInfo(xuid='2535428504476914',
                                             userhash='1674471606081042789',
                                             gamertag='xboxWebapiGamertag',
                                             age_group='Adult',
                                             privileges='123 321 432 654',
                                             user_privileges='123')

    auth_manager.dump(filepath)

    assert os.path.isfile(filepath) is True
