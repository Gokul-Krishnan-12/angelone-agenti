import json
import sys
import traceback

from .config import config_manager
from .scanner import scanner
from .smartapi_client import smart_api_client
from .telegram_bot import telegram_bot
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

        elif method == "get_trades":
            return success(smart_api_client.get_trades())

        elif method == "estimate_charges":
            orders = (
                params.get("orders", [])
                if isinstance(params, dict)
                else (params if isinstance(params, list) else [])
            )
            return success(smart_api_client.estimate_charges(orders))

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
            token = (
                params.get("instrument_token")
                or params.get("instrumentToken")
                or params.get("symbol_token")
                or params.get("token")
            )
            from_date = params.get("from_date") or params.get("fromDate")
            to_date = params.get("to_date") or params.get("toDate")
            interval = params.get("interval", "ONE_DAY")
            exchange = params.get("exchange", "NSE")
            if not token or not from_date or not to_date:
                return error(
                    -32602, "instrument_token, from_date, and to_date are required"
                )
            data = smart_api_client.get_historical_data(
                instrument_token=str(token),
                from_date=str(from_date),
                to_date=str(to_date),
                interval=interval,
                exchange=exchange,
            )
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

        elif method == "ticker_subscribe":
            tokens = params.get("tokens", [])
            ticker_manager.subscribe(tokens)
            return success({"status": "subscribed", "tokens": tokens})

        elif method == "ticker_unsubscribe":
            tokens = params.get("tokens", [])
            ticker_manager.unsubscribe(tokens)
            return success({"status": "unsubscribed", "tokens": tokens})

        elif method == "ticker_status":
            return success(ticker_manager.status())

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

        elif method == "agent_dismiss_signal":
            signal_id = params.get("signalId") or params.get("signal_id", "")
            return success({"dismissed": signal_id})

        elif method == "get_settings":
            return success(config_manager.config)

        elif method == "save_settings":
            config_manager.config.update(params)
            config_manager.save()
            telegram_bot.restart()
            return success({"status": "saved"})

        elif method == "settings_reset":
            config_manager.config["risk"] = config_manager.default_config["risk"].copy()
            config_manager.config["strategies"] = config_manager.default_config[
                "strategies"
            ].copy()
            config_manager.save()
            telegram_bot.restart()
            return success(config_manager.config)

        elif method in ("scan_now", "agent_scan_now"):
            from .fno_universe import get_fno_universe
            from .screener import screener_engine

            custom_watchlist = config_manager.get_watchlist()
            full_universe = list(set(get_fno_universe() + custom_watchlist))

            # Run the dynamic screener for top 35 momentum & in-play F&O stocks
            top_stocks = screener_engine.generate_daily_watchlist(
                universe=full_universe, limit=35
            )
            # Scan top stocks
            signals = scanner.scan_watchlist(top_stocks)
            return success(signals)

        elif method == "log_get_all":
            return success([])

        elif method == "log_clear":
            return success({"status": "cleared"})

        elif method == "watchlist_get":
            return success(config_manager.get_watchlist())

        elif method == "watchlist_add":
            symbol = str(params.get("symbol", "")).upper().strip()
            wl = list(config_manager.get_watchlist())
            if symbol and symbol not in wl:
                wl.append(symbol)
                config_manager.config["watchlist"] = wl
                config_manager.save()
            return success(wl)

        elif method == "watchlist_remove":
            symbol = str(params.get("symbol", "")).upper().strip()
            wl = list(config_manager.get_watchlist())
            if symbol in wl:
                wl.remove(symbol)
                config_manager.config["watchlist"] = wl
                config_manager.save()
            return success(wl)

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

        elif method == "telegram_test":
            from .notifier import notifier

            bot_token = params.get("botToken") or params.get("bot_token")
            chat_id = params.get("chatId") or params.get("chat_id")
            test_msg = (
                "✅ <b>Angel One Trading Agent Connected!</b>\n\n"
                "Telegram notifications are successfully configured.\n"
                "You will receive instant alerts when trades exit and daily P&L session summaries."
            )
            ok, msg = notifier.send_telegram_message_sync(
                test_msg, bot_token=bot_token, chat_id=chat_id
            )
            return success({"success": ok, "message": msg})

        elif method == "telegram_send_exit":
            from .notifier import notifier

            trade = params.get("trade", {})
            notifier.notify_trade_exit(trade)
            return success({"status": "queued"})

        elif method == "telegram_send_summary":
            from .notifier import notifier

            summary = params.get("summary", {})
            notifier.notify_session_summary(summary)
            return success({"status": "queued"})

        elif method == "telegram_bot_status":
            return success({"running": telegram_bot.is_running()})

        elif method == "telegram_bot_start":
            res = telegram_bot.start()
            return success({"started": res, "running": telegram_bot.is_running()})

        elif method == "telegram_bot_stop":
            telegram_bot.stop()
            return success({"stopped": True, "running": False})

        elif method == "swing_scan":
            from .swing_screener import swing_screener

            limit = int(params.get("limit", 15)) if isinstance(params, dict) else 15
            results = swing_screener.run_screener(limit=limit)
            return success(results)

        elif method == "get_last_swing_scan":
            from .swing_screener import swing_screener

            return success(swing_screener.get_last_results())

        else:
            return error(-32601, f"Method '{method}' not found")

    except Exception as e:
        return error(-32000, str(e), traceback.format_exc())


def main():
    try:
        telegram_bot.start()
    except Exception:
        pass

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
