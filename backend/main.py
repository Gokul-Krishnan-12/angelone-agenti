import json
import sys
import traceback

from .config import config_manager
from .scanner import scanner
from .smartapi_client import smart_api_client
from .ticker import ticker_manager
from .trading_engine import trading_engine
from .utils import DateTimeEncoder


def handle_request(req):
    method = req.get("method")
    params = req.get("params", {})
    req_id = req.get("id")

    def success(result):
        return {"jsonrpc": "2.0", "result": result, "id": req_id}

    def error(code, message, data=None):
        return {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message, "data": data},
            "id": req_id,
        }

    try:
        if method == "login":
            creds = config_manager.get_credentials()
            api_key = (
                params.get("api_key") or params.get("apiKey") or creds.get("apiKey")
            )
            client_code = (
                params.get("client_code")
                or params.get("clientCode")
                or params.get("user_id")
                or creds.get("clientCode")
            )
            pin = params.get("pin") or params.get("password") or creds.get("pin")
            totp_secret = (
                params.get("totp_secret")
                or params.get("totpSecret")
                or params.get("totp")
                or creds.get("totpSecret")
            )

            if not api_key:
                return error(-32602, "API Key required")
            if not client_code:
                return error(-32602, "Client Code (User ID) required")
            if not pin:
                return error(-32602, "PIN / Password required")
            if not totp_secret:
                return error(-32602, "TOTP Secret or Authenticator Code required")

            login_res = smart_api_client.login(api_key, client_code, pin, totp_secret)

            config_manager.save_credentials(
                api_key=api_key,
                client_code=client_code,
                pin=pin,
                totp_secret=totp_secret,
                jwt_token=login_res.get("jwt_token", ""),
                refresh_token=login_res.get("refresh_token", ""),
                feed_token=login_res.get("feed_token", ""),
            )

            ticker_manager.start(
                api_key=api_key,
                auth_token=login_res.get("jwt_token", ""),
                client_code=client_code,
                feed_token=login_res.get("feed_token", ""),
            )

            return success(login_res)

        elif method == "check_session":
            creds = config_manager.get_credentials()
            api_key = creds.get("apiKey")
            client_code = creds.get("clientCode")
            pin = creds.get("pin")
            totp_secret = creds.get("totpSecret")
            jwt_token = creds.get("jwtToken")
            feed_token = creds.get("feedToken")

            if not api_key:
                return success({"is_valid": False})

            # Attempt auto-login if full credentials and TOTP secret are stored
            if client_code and pin and totp_secret:
                try:
                    login_res = smart_api_client.login(
                        api_key, client_code, pin, totp_secret
                    )
                    config_manager.save_credentials(
                        api_key=api_key,
                        client_code=client_code,
                        pin=pin,
                        totp_secret=totp_secret,
                        jwt_token=login_res.get("jwt_token", ""),
                        refresh_token=login_res.get("refresh_token", ""),
                        feed_token=login_res.get("feed_token", ""),
                    )
                    ticker_manager.start(
                        api_key=api_key,
                        auth_token=login_res.get("jwt_token", ""),
                        client_code=client_code,
                        feed_token=login_res.get("feed_token", ""),
                    )
                    return success(login_res)
                except Exception:
                    pass

            # Fallback to existing session token
            if jwt_token:
                smart_api_client.init(api_key, client_code or "")
                smart_api_client.set_session_tokens(
                    jwt_token=jwt_token,
                    refresh_token=creds.get("refreshToken", ""),
                    feed_token=feed_token or "",
                    client_code=client_code or "",
                )
                is_valid = False
                refresh_tok = creds.get("refreshToken", "")
                try:
                    profile_res = smart_api_client.smart_api.getProfile(refresh_tok)
                    if profile_res and profile_res.get("status"):
                        is_valid = True
                except Exception:
                    is_valid = False

                if not is_valid and refresh_tok:
                    if smart_api_client.renew_access_token():
                        is_valid = True
                        jwt_token = smart_api_client.jwt_token
                        config_manager.save_credentials(
                            api_key=api_key,
                            client_code=client_code or "",
                            jwt_token=jwt_token,
                            refresh_token=smart_api_client.refresh_token,
                            feed_token=feed_token or "",
                        )

                if is_valid:
                    if feed_token:
                        ticker_manager.start(
                            api_key, jwt_token, client_code or "", feed_token
                        )
                    return success(
                        {
                            "is_valid": True,
                            "user_id": client_code,
                            "jwt_token": jwt_token,
                            "access_token": jwt_token,
                        }
                    )

            return success({"is_valid": False})

        elif method == "logout":
            ticker_manager.stop()
            smart_api_client.set_session_tokens("", "", "", "")
            return success({"status": "logged_out"})

        elif method == "generate_session":
            # For backward compatibility with any direct session generators
            api_key = params.get("api_key") or params.get("apiKey")
            client_code = params.get("client_code") or params.get("clientCode")
            pin = params.get("pin") or params.get("password")
            totp = params.get("totp") or params.get("totp_secret")
            if not api_key or not client_code or not pin or not totp:
                return error(-32602, "api_key, client_code, pin, and totp are required")

            session = smart_api_client.login(api_key, client_code, pin, totp)
            config_manager.save_credentials(
                api_key=api_key,
                client_code=client_code,
                pin=pin,
                totp_secret=totp,
                jwt_token=session.get("jwt_token", ""),
                refresh_token=session.get("refresh_token", ""),
                feed_token=session.get("feed_token", ""),
            )
            ticker_manager.start(
                api_key,
                session.get("jwt_token", ""),
                client_code,
                session.get("feed_token", ""),
            )
            return success(session)

        elif method == "get_positions":
            force = params.get("force", False) if isinstance(params, dict) else False
            return success(smart_api_client.get_positions(force=force))

        elif method == "get_orders":
            force = params.get("force", False) if isinstance(params, dict) else False
            return success(smart_api_client.get_orders(force=force))

        elif method == "get_holdings":
            return success(smart_api_client.get_holdings())

        elif method == "get_margins":
            force = params.get("force", False) if isinstance(params, dict) else False
            return success(smart_api_client.get_margins(force=force))

        elif method == "place_order":
            order_id = smart_api_client.place_order(**params)
            return success({"order_id": order_id})

        elif method == "cancel_order":
            res = smart_api_client.cancel_order(**params)
            return success(res)

        elif method == "modify_order":
            res = smart_api_client.modify_order(**params)
            return success(res)

        elif method == "get_historical":
            data = smart_api_client.get_historical_data(**params)
            return success(data)

        elif method == "get_quote":
            instruments = params.get("instruments", [])
            data = smart_api_client.get_quote(instruments)
            return success(data)

        elif method == "get_ltp":
            instruments = params.get("instruments", [])
            data = smart_api_client.get_ltp(instruments)
            return success(data)

        elif method == "get_ohlc":
            instruments = params.get("instruments", [])
            data = smart_api_client.get_ohlc(instruments)
            return success(data)

        elif method == "get_instruments":
            exchange = params.get("exchange", "NSE")
            instruments = smart_api_client.get_instruments(exchange)
            return success(instruments)

        elif method == "search_instruments":
            query = params.get("query", "")
            exchange = params.get("exchange", "NSE")
            results = smart_api_client.search_instruments(query, exchange)
            return success(results)

        elif method == "start_agent":
            mode = (
                params.get("mode", "confirm") if isinstance(params, dict) else "confirm"
            )
            trading_engine.start(mode)
            return success({"status": "started", "mode": mode})

        elif method == "stop_agent":
            trading_engine.stop()
            return success({"status": "stopped"})

        elif method == "agent_status":
            return success(trading_engine.status())

        elif method == "get_settings":
            return success(config_manager.config)

        elif method == "save_settings":
            config_manager.config.update(params)
            config_manager.save()
            return success({"status": "saved"})

        elif method == "scan_now":
            from .nifty_universe import get_nifty50_universe
            from .screener import screener_engine

            custom_watchlist = config_manager.get_watchlist()
            full_universe = list(set(get_nifty50_universe() + custom_watchlist))

            # Run the dynamic screener
            top_stocks = screener_engine.generate_daily_watchlist(
                universe=full_universe, limit=12
            )
            # Scan top stocks
            signals = scanner.scan_watchlist(top_stocks)
            return success(signals)

        elif method == "dashboard_summary":
            force = params.get("force", False) if isinstance(params, dict) else False
            margins = smart_api_client.get_margins(force=force)
            equity_margin = margins.get("equity", {})
            available_margin = equity_margin.get("available", {}).get("live_balance", 0)
            if not available_margin:
                available_margin = equity_margin.get("net", 0)

            positions = smart_api_client.get_positions(force=force).get("net", [])
            total_pnl = sum(p.get("pnl", p.get("m2m", 0)) for p in positions)
            realised_pnl = sum(p.get("realised", 0) for p in positions)
            unrealised_pnl = sum(p.get("unrealised", 0) for p in positions)

            calculated_used_margin = 0
            for p in positions:
                if p.get("quantity", 0) != 0:
                    multiplier = 0.2 if p.get("product") in ("MIS", "INTRADAY") else 1.0
                    avg_price = p.get("averagePrice", 0)
                    if avg_price == 0:
                        avg_price = (
                            p.get("buyPrice", 0)
                            if p.get("quantity", 0) > 0
                            else p.get("sellPrice", 0)
                        )
                    calculated_used_margin += (
                        abs(p.get("quantity", 0)) * avg_price * multiplier
                    )

            used_margin = calculated_used_margin

            trades_today = len(positions)
            winning_trades = sum(
                1 for p in positions if p.get("pnl", p.get("m2m", 0)) > 0
            )
            losing_trades = sum(
                1 for p in positions if p.get("pnl", p.get("m2m", 0)) < 0
            )
            win_rate = (winning_trades / trades_today * 100) if trades_today > 0 else 0

            summary = {
                "totalPnl": round(total_pnl, 2),
                "realisedPnl": round(realised_pnl, 2),
                "unrealisedPnl": round(unrealised_pnl, 2),
                "tradesToday": trades_today,
                "winningTrades": winning_trades,
                "losingTrades": losing_trades,
                "winRate": round(win_rate, 2),
                "availableMargin": available_margin,
                "usedMargin": used_margin,
            }
            return success(summary)

        elif method == "execute_signal":
            res = trading_engine.execute_signal(params.get("signal", {}))
            return success({"executed": res})

        else:
            return error(-32601, f"Method '{method}' not found")

    except Exception as e:
        return error(-32000, str(e), traceback.format_exc())


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            res = {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None,
            }
            print(json.dumps(res))
            sys.stdout.flush()
            continue

        res = handle_request(req)
        print(json.dumps(res, cls=DateTimeEncoder))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
