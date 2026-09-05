import { pythonBridge } from './python-bridge';
import { AuthState, SmartApiCredentials } from '../shared/types';

class AuthManager {
  public async startLogin(
    creds:
      | SmartApiCredentials
      | {
          apiKey: string;
          apiSecret?: string;
          clientCode?: string;
          pin?: string;
          totpSecret?: string;
          totp?: string;
          userId?: string;
          password?: string;
        }
  ): Promise<AuthState> {
    const apiKey = creds.apiKey;
    const clientCode =
      (creds as any).clientCode || (creds as any).userId || '';
    const pin = (creds as any).pin || (creds as any).password || '';
    const totpSecret =
      (creds as any).totpSecret || (creds as any).totp || '';

    if (!apiKey) {
      throw new Error('API Key is required');
    }
    if (!clientCode) {
      throw new Error('Client Code (User ID) is required');
    }
    if (!pin) {
      throw new Error('PIN / Password is required');
    }
    if (!totpSecret) {
      throw new Error('TOTP Secret or Authenticator code is required');
    }

    try {
      const response = await pythonBridge.call('login', {
        api_key: apiKey,
        client_code: clientCode,
        pin: pin,
        totp_secret: totpSecret,
      });

      return {
        isLoggedIn: true,
        credentials: {
          apiKey,
          clientCode,
          pin,
          totpSecret,
          jwtToken: response.jwt_token || response.access_token,
          accessToken: response.access_token || response.jwt_token,
          feedToken: response.feed_token,
          userId: response.user_id || clientCode,
          userName: response.user_name || clientCode,
        },
        loginUrl: null,
        error: null,
      };
    } catch (error: any) {
      return {
        isLoggedIn: false,
        credentials: null,
        loginUrl: null,
        error: error.message || 'Failed to authenticate with Angel One SmartAPI',
      };
    }
  }

  public async checkSession(): Promise<boolean> {
    try {
      const response = await pythonBridge.call('check_session');
      return !!response?.is_valid;
    } catch (e) {
      return false;
    }
  }

  public async logout(): Promise<void> {
    try {
      await pythonBridge.call('logout');
    } catch (e) {
      console.error('Error during logout:', e);
    }
  }
}

export const authManager = new AuthManager();
