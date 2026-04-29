#property strict

#include <Trade/Trade.mqh>
CTrade trade;

input string ApiUrl = "http://127.0.0.1:8000/analyze";
input bool DryRun = true;
input bool DemoMode = true;
input bool LiveMode = false;
input bool EnableVision = false;
input bool EnableMt5FileLogging = true;
input double LotSize = 0.01;
input int SlippagePoints = 20;
input long MagicNumber = 20260427;
input ENUM_TIMEFRAMES HigherTimeframe = PERIOD_H1;
input int OhlcBars = 10;
input int AtrPeriod = 14;
input int RsiPeriod = 14;
input int FastEma = 20;
input int SlowEma = 50;
input string VisionImageMime = "image/png";
input string Mt5LogFileName = "mt5_ai_bridge_log.csv";
input bool SaveMt5PayloadFiles = true;
input string Mt5PayloadFolder = "mt5_payloads";
input bool EnableMt5NewsGuard = true;
input int NewsHighImpactBeforeMinutes = 30;
input int NewsHighImpactAfterMinutes = 30;
input int NewsMediumImpactBeforeMinutes = 15;
input int NewsMediumImpactAfterMinutes = 15;

struct DecisionResult
{
   string decision_id;
   string decision;
   int confidence;
   double entry;
   double stop_loss;
   double take_profit;
   double risk_reward;
   bool passed_filter;
   string filter_reason;
   string raw_response;
   string phase;
};

string ExtractDecisionSubtree(string response)
{
   string needle = "\"decision\":";
   int pos = StringFind(response, needle);
   if(pos < 0)
      return response;
   int start = pos + StringLen(needle);
   while(start < StringLen(response) && StringGetCharacter(response, start) != '{')
      start++;
   if(start >= StringLen(response))
      return response;

   int depth = 0;
   for(int i = start; i < StringLen(response); i++)
   {
      ushort ch = StringGetCharacter(response, i);
      if(ch == '{') depth++;
      if(ch == '}') depth--;
      if(depth == 0)
         return StringSubstr(response, start, i - start + 1);
   }
   return response;
}

static datetime g_lastBarTime = 0;
static long g_lastTrackedPositionTicket = -1;
static double g_lastTrackedEntryPrice = 0.0;
static double g_lastTrackedStopLoss = 0.0;
static double g_lastTrackedTakeProfit = 0.0;
static string g_lastTrackedDecision = "";
static string g_lastTrackedDecisionId = "";

int OnInit()
{
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(SlippagePoints);
   Print("AiTraderEA initialized. DryRun=", DryRun, " DemoMode=", DemoMode, " LiveMode=", LiveMode);
   EnsureMt5LogHeader();
   return(INIT_SUCCEEDED);
}

void OnTick()
{
   TrackClosedPositionResult();

   if(!IsNewCandle())
      return;

   Print("New candle detected. Symbol=", _Symbol, " TF=", TimeframeToString(PERIOD_CURRENT), " Mode=", GetModeString());

   string newsReason = "";
   if(HasMt5NewsBlackout(_Symbol, newsReason))
   {
      Print("MT5 news blackout active: ", newsReason);
      LogBridgeEvent("mt5_news_blackout", "", "", false, newsReason);
      return;
   }

   string payload = BuildMarketContextJson();
   if(payload == "")
   {
      Print("BuildMarketContextJson failed");
      LogBridgeEvent("build_market_failed", "", "", false, "payload_empty");
      return;
   }

   Print("Payload built. bytes=", StringLen(payload));
   SaveDebugSnapshot("request", payload);

   string response = PostAnalyzeRequest(payload);
   if(response == "")
   {
      Print("Analyze request returned empty response");
      SaveDebugSnapshot("response_empty", "");
      LogBridgeEvent("analyze_empty_response", payload, "", false, "empty_response");
      return;
   }

   Print("Analyze response length=", StringLen(response));
   Print("Analyze response: ", response);
   SaveDebugSnapshot("response", response);

   DecisionResult result;
   if(!ParseDecisionFromResponse(response, result))
   {
      Print("ParseDecisionFromResponse failed");
      LogBridgeEvent("parse_failed", payload, response, false, "parse_failed");
      return;
   }

   if(!ValidateDecisionResult(result))
   {
      Print("ValidateDecisionResult failed");
      LogBridgeEvent("decision_invalid", payload, response, false, "decision_invalid");
      return;
   }

   LogBridgeEvent("decision_received", payload, response, result.passed_filter, result.filter_reason);

   if(DryRun)
   {
      Print("DryRun active, skipping execution. decision=", result.decision, " passed_filter=", result.passed_filter, " reason=", result.filter_reason);
      LogBridgeEvent("dry_run_skip", payload, response, result.passed_filter, result.filter_reason);
      return;
   }

   if(!result.passed_filter)
   {
      Print("Decision blocked by filter: ", result.filter_reason);
      LogBridgeEvent("filter_blocked", payload, response, false, result.filter_reason);
      return;
   }

   if(result.decision != "BUY" && result.decision != "SELL")
   {
      Print("Non-executable decision: ", result.decision);
      LogBridgeEvent("non_executable_decision", payload, response, false, result.decision);
      return;
   }

   ExecuteApprovedTrade(result);
}

bool IsNewCandle()
{
   datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(currentBarTime == 0)
      return false;
   if(currentBarTime == g_lastBarTime)
      return false;
   g_lastBarTime = currentBarTime;
   return true;
}

string EscapeJson(string value)
{
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   StringReplace(value, "\r", " ");
   StringReplace(value, "\n", " ");
   return value;
}

string TimeframeToString(ENUM_TIMEFRAMES tf)
{
   switch(tf)
   {
      case PERIOD_M1: return "M1";
      case PERIOD_M5: return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1: return "H1";
      case PERIOD_H4: return "H4";
      case PERIOD_D1: return "D1";
      default: return "UNKNOWN";
   }
}

string GetModeString()
{
   if(LiveMode)
      return "live";
   if(DemoMode)
      return "demo";
   return "dry_run";
}

string GetSessionName()
{
   MqlDateTime dt;
   TimeToStruct(TimeGMT(), dt);
   int h = dt.hour;
   if(h >= 0 && h < 7) return "Asia";
   if(h >= 7 && h < 12) return "London";
   if(h >= 12 && h < 16) return "Overlap";
   if(h >= 16 && h < 21) return "NewYork";
   return "Asia";
}

int CountOpenPositionsBySymbol()
{
   int count = 0;
   for(int i = 0; i < PositionsTotal(); i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionSelectByTicket(ticket))
      {
         string symbol = PositionGetString(POSITION_SYMBOL);
         if(symbol == _Symbol)
            count++;
      }
   }
   return count;
}

double GetIndicatorValue(int handle)
{
   double buffer[];
   ArraySetAsSeries(buffer, true);
   if(CopyBuffer(handle, 0, 0, 1, buffer) < 1)
      return 0.0;
   return buffer[0];
}

string BuildOhlcArrayJson()
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, PERIOD_CURRENT, 1, OhlcBars, rates);
   if(copied < 3)
      return "[]";

   string out = "[";
   for(int i = copied - 1; i >= 0; i--)
   {
      MqlDateTime dt;
      TimeToStruct(rates[i].time, dt);
      string ts = StringFormat("%04d-%02d-%02d %02d:%02d", dt.year, dt.mon, dt.day, dt.hour, dt.min);
      out += StringFormat("{\"t\":\"%s\",\"o\":%.5f,\"h\":%.5f,\"l\":%.5f,\"c\":%.5f}", ts, rates[i].open, rates[i].high, rates[i].low, rates[i].close);
      if(i > 0)
         out += ",";
   }
   out += "]";
   return out;
}

string Base64Encode(const uchar &data[])
{
   string alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
   string output = "";
   int len = ArraySize(data);
   for(int i = 0; i < len; i += 3)
   {
      int b0 = data[i];
      int b1 = (i + 1 < len) ? data[i + 1] : 0;
      int b2 = (i + 2 < len) ? data[i + 2] : 0;
      int triple = (b0 << 16) | (b1 << 8) | b2;

      output += StringSubstr(alphabet, (triple >> 18) & 63, 1);
      output += StringSubstr(alphabet, (triple >> 12) & 63, 1);
      output += (i + 1 < len) ? StringSubstr(alphabet, (triple >> 6) & 63, 1) : "=";
      output += (i + 2 < len) ? StringSubstr(alphabet, triple & 63, 1) : "=";
   }
   return output;
}

string TryCaptureChartImageBase64()
{
   if(!EnableVision)
      return "";

   string fileName = "mt5_ai_chart.png";
   if(!ChartScreenShot(0, fileName, 1280, 720, ALIGN_RIGHT))
      return "";

   int handle = FileOpen(fileName, FILE_READ | FILE_BIN);
   if(handle == INVALID_HANDLE)
      return "";

   int size = (int)FileSize(handle);
   if(size <= 0)
   {
      FileClose(handle);
      return "";
   }

   uchar bytes[];
   ArrayResize(bytes, size);
   FileReadArray(handle, bytes, 0, size);
   FileClose(handle);
   return Base64Encode(bytes);
}

string NormalizeSymbolForNews(string symbol)
{
   string s = symbol;
   StringToUpper(s);
   StringReplace(s, ".", "");
   StringReplace(s, "_", "");
   StringReplace(s, "-", "");
   return s;
}

bool SymbolHasCurrency(string symbol, string currency)
{
   string normalized = NormalizeSymbolForNews(symbol);
   if(StringLen(normalized) >= 6)
   {
      string a = StringSubstr(normalized, 0, 3);
      string b = StringSubstr(normalized, 3, 3);
      if(a == currency || b == currency)
         return true;
   }
   if((StringFind(normalized, "XAUUSD") >= 0 || StringFind(normalized, "XAGUSD") >= 0 || StringFind(normalized, "BTCUSD") >= 0 || StringFind(normalized, "ETHUSD") >= 0 || StringFind(normalized, "US30") >= 0 || StringFind(normalized, "NAS100") >= 0 || StringFind(normalized, "SPX500") >= 0) && currency == "USD")
      return true;
   return false;
}

bool IsWithinNewsWindow(datetime eventTime, int beforeMinutes, int afterMinutes)
{
   datetime nowTime = TimeGMT();
   datetime start = eventTime - beforeMinutes * 60;
   datetime end = eventTime + afterMinutes * 60;
   return (nowTime >= start && nowTime <= end);
}

bool HasMt5NewsBlackout(string symbol, string &reason)
{
   reason = "";
   if(!EnableMt5NewsGuard)
      return false;

   // MT5 economic calendar wiring is broker/terminal dependent.
   // This skeleton uses a conservative stub path and is ready for real CalendarValueHistory/CalendarEventById wiring.
   // For now it checks a terminal global variable if present, so the path is testable without full calendar integration.
   string gvName = "MT5_NEWS_BLACKOUT_" + NormalizeSymbolForNews(symbol);
   if(GlobalVariableCheck(gvName))
   {
      double active = GlobalVariableGet(gvName);
      if(active > 0)
      {
         reason = "news_blackout_mt5_manual_stub";
         return true;
      }
   }

   return false;
}

string BuildNewsContextJson()
{
   string reason = "";
   bool blocked = HasMt5NewsBlackout(_Symbol, reason);
   return StringFormat("{\"mt5_news_available\":true,\"mt5_blackout_active\":%s,\"mt5_reason\":\"%s\"}", blocked ? "true" : "false", EscapeJson(reason));
}

string BuildMarketContextJson()
{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double spreadPoints = (ask - bid) / _Point;

   int ema20Handle = iMA(_Symbol, PERIOD_CURRENT, FastEma, 0, MODE_EMA, PRICE_CLOSE);
   int ema50Handle = iMA(_Symbol, PERIOD_CURRENT, SlowEma, 0, MODE_EMA, PRICE_CLOSE);
   int rsiHandle = iRSI(_Symbol, PERIOD_CURRENT, RsiPeriod, PRICE_CLOSE);
   int atrHandle = iATR(_Symbol, PERIOD_CURRENT, AtrPeriod);
   int macdHandle = iMACD(_Symbol, PERIOD_CURRENT, 12, 26, 9, PRICE_CLOSE);
   int ema20HtfHandle = iMA(_Symbol, HigherTimeframe, FastEma, 0, MODE_EMA, PRICE_CLOSE);
   int ema50HtfHandle = iMA(_Symbol, HigherTimeframe, SlowEma, 0, MODE_EMA, PRICE_CLOSE);

   if(ema20Handle == INVALID_HANDLE || ema50Handle == INVALID_HANDLE || rsiHandle == INVALID_HANDLE || atrHandle == INVALID_HANDLE || macdHandle == INVALID_HANDLE || ema20HtfHandle == INVALID_HANDLE || ema50HtfHandle == INVALID_HANDLE)
      return "";

   double ema20 = GetIndicatorValue(ema20Handle);
   double ema50 = GetIndicatorValue(ema50Handle);
   double rsi = GetIndicatorValue(rsiHandle);
   double atr = GetIndicatorValue(atrHandle);
   double macdMain[];
   double macdSignal[];
   ArraySetAsSeries(macdMain, true);
   ArraySetAsSeries(macdSignal, true);
   CopyBuffer(macdHandle, 0, 0, 1, macdMain);
   CopyBuffer(macdHandle, 1, 0, 1, macdSignal);
   double macdMainVal = ArraySize(macdMain) > 0 ? macdMain[0] : 0.0;
   double macdSignalVal = ArraySize(macdSignal) > 0 ? macdSignal[0] : 0.0;

   double ema20Htf = GetIndicatorValue(ema20HtfHandle);
   double ema50Htf = GetIndicatorValue(ema50HtfHandle);
   string htfTrend = "neutral";
   if(ema20Htf > ema50Htf) htfTrend = "bullish";
   else if(ema20Htf < ema50Htf) htfTrend = "bearish";

   string marketStructure = ema20 > ema50 ? "higher_highs_higher_lows" : "lower_highs_lower_lows";
   string momentum = macdMainVal >= macdSignalVal ? "bullish" : "bearish";

   MqlRates srRates[];
   ArraySetAsSeries(srRates, true);
   int srCopied = CopyRates(_Symbol, PERIOD_CURRENT, 1, 20, srRates);
   double lowest = bid;
   double secondLowest = bid;
   double highest = ask;
   double secondHighest = ask;
   for(int i = 0; i < srCopied; i++)
   {
      if(i == 0 || srRates[i].low < lowest)
      {
         secondLowest = lowest;
         lowest = srRates[i].low;
      }
      if(i == 0 || srRates[i].high > highest)
      {
         secondHighest = highest;
         highest = srRates[i].high;
      }
   }

   string ohlcJson = BuildOhlcArrayJson();
   int openPositions = CountOpenPositionsBySymbol();
   bool hasBuy = false;
   bool hasSell = false;
   for(int i = 0; i < PositionsTotal(); i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL) == _Symbol)
      {
         long posType = PositionGetInteger(POSITION_TYPE);
         if(posType == POSITION_TYPE_BUY) hasBuy = true;
         if(posType == POSITION_TYPE_SELL) hasSell = true;
      }
   }

   string imageBase64 = TryCaptureChartImageBase64();
   string visionFields = "";
   if(imageBase64 != "")
      visionFields = StringFormat(",\"chart_image_base64\":\"%s\",\"chart_image_mime\":\"%s\"", imageBase64, VisionImageMime);

   string newsContext = BuildNewsContextJson();

   string json = StringFormat(
      "{\"symbol\":\"%s\",\"timeframe\":\"%s\",\"higher_timeframe\":\"%s\",\"session\":\"%s\",\"bid\":%.5f,\"ask\":%.5f,\"spread\":%.2f,\"ohlc\":%s,\"indicators\":{\"ema20\":%.5f,\"ema50\":%.5f,\"rsi14\":%.2f,\"macd_main\":%.5f,\"macd_signal\":%.5f,\"atr14\":%.5f},\"support_resistance\":{\"support_1\":%.5f,\"support_2\":%.5f,\"resistance_1\":%.5f,\"resistance_2\":%.5f},\"trend_context\":{\"htf_trend\":\"%s\",\"market_structure\":\"%s\",\"momentum\":\"%s\"},\"position_context\":{\"open_positions\":%d,\"has_buy_position\":%s,\"has_sell_position\":%s},\"news_context\":%s,\"mode\":\"%s\"%s}",
      EscapeJson(_Symbol),
      TimeframeToString(PERIOD_CURRENT),
      TimeframeToString(HigherTimeframe),
      GetSessionName(),
      bid,
      ask,
      spreadPoints,
      ohlcJson,
      ema20,
      ema50,
      rsi,
      macdMainVal,
      macdSignalVal,
      atr,
      lowest,
      secondLowest,
      highest,
      secondHighest,
      htfTrend,
      marketStructure,
      momentum,
      openPositions,
      hasBuy ? "true" : "false",
      hasSell ? "true" : "false",
      newsContext,
      GetModeString(),
      visionFields
   );

   IndicatorRelease(ema20Handle);
   IndicatorRelease(ema50Handle);
   IndicatorRelease(rsiHandle);
   IndicatorRelease(atrHandle);
   IndicatorRelease(macdHandle);
   IndicatorRelease(ema20HtfHandle);
   IndicatorRelease(ema50HtfHandle);
   return json;
}

string PostAnalyzeRequest(string payload)
{
   string headers = "Content-Type: application/json\r\n";
   uchar data[];
   uchar result[];
   string responseHeaders = "";
   int size = StringToCharArray(payload, data, 0, WHOLE_ARRAY, CP_UTF8);
   if(size > 0)
      ArrayResize(data, size - 1);
   int timeout = 30000;
   ResetLastError();
   int status = WebRequest("POST", ApiUrl, headers, timeout, data, result, responseHeaders);
   if(status == -1)
   {
      Print("WebRequest failed. Error=", GetLastError());
      return "";
   }
   string response = CharArrayToString(result, 0, -1, CP_UTF8);
   return response;
}

bool ExtractJsonBool(string text, string key, bool &value)
{
   string needle = "\"" + key + "\":";
   int pos = StringFind(text, needle);
   if(pos < 0) return false;
   string tail = StringSubstr(text, pos + StringLen(needle));
   if(StringFind(tail, "true") == 0)
   {
      value = true;
      return true;
   }
   if(StringFind(tail, "false") == 0)
   {
      value = false;
      return true;
   }
   return false;
}

bool ExtractJsonNumber(string text, string key, double &value)
{
   string needle = "\"" + key + "\":";
   int pos = StringFind(text, needle);
   if(pos < 0) return false;
   int start = pos + StringLen(needle);
   int end = start;
   while(end < StringLen(text))
   {
      ushort ch = StringGetCharacter(text, end);
      if((ch >= '0' && ch <= '9') || ch == '.' || ch == '-')
         end++;
      else
         break;
   }
   string raw = StringSubstr(text, start, end - start);
   value = StringToDouble(raw);
   return true;
}

bool ExtractJsonString(string text, string key, string &value)
{
   string needle = "\"" + key + "\":\"";
   int pos = StringFind(text, needle);
   if(pos < 0) return false;
   int start = pos + StringLen(needle);
   int end = start;
   while(end < StringLen(text))
   {
      if(StringGetCharacter(text, end) == '"' && StringGetCharacter(text, end - 1) != '\\')
         break;
      end++;
   }
   value = StringSubstr(text, start, end - start);
   return true;
}

bool ParseDecisionFromResponse(string response, DecisionResult &result)
{
   result.raw_response = response;
   string decisionBlock = ExtractDecisionSubtree(response);
   if(!ExtractJsonString(decisionBlock, "decision_id", result.decision_id)) result.decision_id = "";
   if(!ExtractJsonString(decisionBlock, "decision", result.decision)) return false;
   double confidence = 0, entry = 0, sl = 0, tp = 0, rr = 0;
   if(!ExtractJsonNumber(decisionBlock, "confidence", confidence)) return false;
   if(!ExtractJsonNumber(decisionBlock, "entry", entry)) entry = 0;
   if(!ExtractJsonNumber(decisionBlock, "stop_loss", sl)) sl = 0;
   if(!ExtractJsonNumber(decisionBlock, "take_profit", tp)) tp = 0;
   if(!ExtractJsonNumber(decisionBlock, "risk_reward", rr)) rr = 0;
   result.confidence = (int)confidence;
   result.entry = entry;
   result.stop_loss = sl;
   result.take_profit = tp;
   result.risk_reward = rr;
   if(!ExtractJsonBool(decisionBlock, "passed_filter", result.passed_filter)) result.passed_filter = false;
   if(!ExtractJsonString(decisionBlock, "filter_reason", result.filter_reason)) result.filter_reason = "unknown";
   if(!ExtractJsonString(decisionBlock, "phase", result.phase)) result.phase = "unknown";
   return true;
}

bool ValidateDecisionResult(DecisionResult &result)
{
   if(result.decision != "BUY" && result.decision != "SELL" && result.decision != "WAIT")
      return false;
   if(result.confidence < 0 || result.confidence > 100)
      return false;
   if(result.decision == "BUY")
   {
      if(!(result.stop_loss < result.entry && result.entry < result.take_profit))
         return false;
   }
   if(result.decision == "SELL")
   {
      if(!(result.take_profit < result.entry && result.entry < result.stop_loss))
         return false;
   }
   return true;
}

void EnsureMt5LogHeader()
{
   if(!EnableMt5FileLogging)
      return;
   int handle = FileOpen(Mt5LogFileName, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return;
   if(FileSize(handle) == 0)
      FileWrite(handle, "time", "event", "symbol", "decision", "passed_filter", "reason", "payload", "response");
   FileClose(handle);
}

void LogBridgeEvent(string eventName, string payload, string response, bool passedFilter, string reason)
{
   if(!EnableMt5FileLogging)
      return;
   int handle = FileOpen(Mt5LogFileName, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return;
   FileSeek(handle, 0, SEEK_END);
   FileWrite(handle, TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES | TIME_SECONDS), eventName, _Symbol, "", passedFilter ? "true" : "false", reason, payload, response);
   FileClose(handle);
}

string BuildSnapshotFileName(string kind)
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return StringFormat("%s\\%04d-%02d-%02d_%02d-%02d-%02d_%s_%s_%s.json",
      Mt5PayloadFolder,
      dt.year, dt.mon, dt.day, dt.hour, dt.min, dt.sec,
      NormalizeSymbolForNews(_Symbol),
      TimeframeToString(PERIOD_CURRENT),
      kind);
}

void SaveDebugSnapshot(string kind, string content)
{
   if(!SaveMt5PayloadFiles)
      return;
   FolderCreate(Mt5PayloadFolder);
   string fileName = BuildSnapshotFileName(kind);
   int handle = FileOpen(fileName, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      Print("Failed to open snapshot file: ", fileName, " error=", GetLastError());
      return;
   }
   FileWriteString(handle, content);
   FileClose(handle);
   Print("Saved snapshot: ", fileName);
}

string BuildTradeResultPayload(DecisionResult &result, string positionTicket, double closePrice, double pnl, string finalResult, string notes)
{
   return StringFormat(
      "{\"symbol\":\"%s\",\"timeframe\":\"%s\",\"mode\":\"%s\",\"decision_id\":\"%s\",\"decision\":\"%s\",\"position_ticket\":\"%s\",\"entry_price\":%.5f,\"close_price\":%.5f,\"stop_loss\":%.5f,\"take_profit\":%.5f,\"pnl\":%.2f,\"result\":\"%s\",\"notes\":\"%s\"}",
      EscapeJson(_Symbol),
      TimeframeToString(PERIOD_CURRENT),
      GetModeString(),
      EscapeJson(result.decision_id),
      result.decision,
      positionTicket,
      result.entry,
      closePrice,
      result.stop_loss,
      result.take_profit,
      pnl,
      finalResult,
      EscapeJson(notes)
   );
}

string PostTradeResult(string payload)
{
   string headers = "Content-Type: application/json\r\n";
   uchar data[];
   uchar result[];
   string responseHeaders = "";
   StringToCharArray(payload, data, 0, WHOLE_ARRAY, CP_UTF8);
   ResetLastError();
   string resultUrl = ApiUrl;
   StringReplace(resultUrl, "/analyze", "/trade-result");
   int status = WebRequest("POST", resultUrl, headers, 30000, data, result, responseHeaders);
   if(status == -1)
   {
      Print("Trade result WebRequest failed. Error=", GetLastError());
      return "";
   }
   return CharArrayToString(result, 0, -1, CP_UTF8);
}

void TrackOpenPosition(DecisionResult &result)
{
   g_lastTrackedPositionTicket = (long)trade.ResultOrder();
   g_lastTrackedEntryPrice = result.entry;
   g_lastTrackedStopLoss = result.stop_loss;
   g_lastTrackedTakeProfit = result.take_profit;
   g_lastTrackedDecision = result.decision;
   g_lastTrackedDecisionId = result.decision_id;
}

void TrackClosedPositionResult()
{
   if(g_lastTrackedPositionTicket < 0)
      return;

   if(PositionSelectByTicket((ulong)g_lastTrackedPositionTicket))
      return;

   HistorySelect(TimeCurrent() - 86400 * 7, TimeCurrent());
   double pnl = 0.0;
   double closePrice = 0.0;
   bool found = false;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
   {
      ulong dealTicket = HistoryDealGetTicket(i);
      if(dealTicket == 0)
         continue;
      long orderId = (long)HistoryDealGetInteger(dealTicket, DEAL_ORDER);
      if(orderId == g_lastTrackedPositionTicket)
      {
         pnl += HistoryDealGetDouble(dealTicket, DEAL_PROFIT);
         closePrice = HistoryDealGetDouble(dealTicket, DEAL_PRICE);
         found = true;
      }
   }

   if(found)
   {
      string resultLabel = pnl >= 0.0 ? "win" : "loss";
      DecisionResult temp;
      temp.decision_id = g_lastTrackedDecisionId;
      temp.decision = g_lastTrackedDecision;
      temp.entry = g_lastTrackedEntryPrice;
      temp.stop_loss = g_lastTrackedStopLoss;
      temp.take_profit = g_lastTrackedTakeProfit;
      string resultPayload = BuildTradeResultPayload(temp, IntegerToString((int)g_lastTrackedPositionTicket), closePrice, pnl, resultLabel, "closed_position_report");
      string ingestResponse = PostTradeResult(resultPayload);
      Print("Closed trade result ingest response: ", ingestResponse);
      LogBridgeEvent("trade_closed_reported", "", resultPayload, true, resultLabel);
   }

   g_lastTrackedPositionTicket = -1;
   g_lastTrackedEntryPrice = 0.0;
   g_lastTrackedStopLoss = 0.0;
   g_lastTrackedTakeProfit = 0.0;
   g_lastTrackedDecision = "";
   g_lastTrackedDecisionId = "";
}

bool ExecuteApprovedTrade(DecisionResult &result)
{
   if(LiveMode == false && DemoMode == false)
   {
      Print("Execution disabled, neither live nor demo mode enabled");
      return false;
   }

   bool ok = false;
   if(result.decision == "BUY")
      ok = trade.Buy(LotSize, _Symbol, 0.0, result.stop_loss, result.take_profit, "ai-buy");
   else if(result.decision == "SELL")
      ok = trade.Sell(LotSize, _Symbol, 0.0, result.stop_loss, result.take_profit, "ai-sell");

   if(!ok)
   {
      Print("Trade execution failed. Retcode=", trade.ResultRetcode(), " comment=", trade.ResultComment());
      LogBridgeEvent("trade_failed", "", result.raw_response, false, trade.ResultComment());
   }
   else
   {
      string ticket = IntegerToString((int)trade.ResultOrder());
      Print("Trade executed. Order=", trade.ResultOrder(), " deal=", trade.ResultDeal(), " decision=", result.decision);
      LogBridgeEvent("trade_executed", "", result.raw_response, true, result.decision);
      TrackOpenPosition(result);
      string resultPayload = BuildTradeResultPayload(result, ticket, result.entry, 0.0, "open", "initial_ingest_after_execution");
      string ingestResponse = PostTradeResult(resultPayload);
      Print("Trade result ingest response: ", ingestResponse);
   }
   return ok;
}
