# LMView UML Diagram Guide for System Analysis and Design

This document summarizes the diagram set recommended for the LMView thesis system analysis and design section. The revised approach keeps the diagrams balanced: use cases are grouped into larger functional areas, the class diagram describes the logical domain model, and the sequence diagrams focus on four representative user-driven flows.

## 1. Recommended Diagram Order

Present the diagrams in this order:

1. Use Case Diagram
2. Component Diagram
3. 3-Node Docker Swarm Deployment Diagram
4. ERD / Database Diagram
5. Class Diagram
6. Activity Diagram: chart loading and data fallback
7. Sequence Diagram: login
8. Sequence Diagram: real-time chart viewing and symbol/timeframe changes
9. Sequence Diagram: AI Assistant question
10. Sequence Diagram: market news reading

Reason for this order:

- The use case diagram sets the user-facing scope.
- The component and deployment diagrams explain LMView as a distributed Lambda Architecture system deployed on Docker Swarm.
- The ERD and class diagram describe persistent data and logical business objects.
- The activity and sequence diagrams then prove how the most important workflows execute.

## 2. Use Case Diagram

### Purpose

The use case diagram describes what users can do with the system. Avoid listing too many small use cases at the same level. Group small actions under larger use cases so the diagram stays readable and maps cleanly to the sequence diagrams.

### Actors

- Guest: unauthenticated visitor.
- User: authenticated user.
- Admin: system administrator.

Actor relationships:

- User inherits from Guest.
- Admin inherits from User.

### Main Use Cases

1. Register / Login
2. View and Analyze Market Chart
3. View Supporting Market Data
4. Read Market News
5. Ask AI Assistant
6. Customize Account and Interface
7. Administer System

### Include / Extend Details

Register / Login:

- include: Enter login information
- include: Authenticate account
- include: Create user session

View and Analyze Market Chart:

- include: Load candle data
- include: Receive real-time updates
- extend: Change symbol/timeframe
- extend: Enable/disable technical indicators

View Supporting Market Data:

- include: View ticker
- include: View order book
- include: View recent trades

Read Market News:

- include: Load news list
- extend: Search/filter news
- extend: View news detail

Ask AI Assistant:

- include: Submit question
- include: Collect chart context
- include: Retrieve knowledge/news context
- include: Save chat history
- extend: Rate assistant response

Customize Account and Interface:

- include: Update theme/language
- include: Update default symbol/timeframe
- extend: Manage watchlist

Administer System:

- include: Manage users
- include: View health checks
- include: View service status

### Drawing Notes

Do not draw every small action as a separate top-level use case. For example, `Change symbol`, `Change timeframe`, `Enable RSI`, and `Enable MACD` should belong under `View and Analyze Market Chart`.

## 3. Component Diagram

### Purpose

The component diagram describes the major software blocks and how they communicate. This is the most important diagram for explaining the Lambda Architecture of LMView.

### Components

- React Frontend
- Nginx
- FastAPI Backend
- AI Service
- News Service
- Binance API
- Kafka
- Flink
- Spark
- Redis Sentinel
- InfluxDB
- PostgreSQL
- MinIO / Iceberg
- Trino
- Prometheus / Grafana / Loki

### Connections

Frontend:

- React Frontend -> Nginx: HTTPS and WebSocket.
- Nginx -> FastAPI Backend: reverse proxy.

Serving layer:

- FastAPI -> Redis Sentinel: ticker, hot candles, order book, recent trades.
- FastAPI -> InfluxDB: warm candle storage.
- FastAPI -> Trino -> Iceberg/MinIO: historical data and market overview.
- FastAPI -> PostgreSQL: users, settings, AI chat, knowledge, news.

Data pipeline:

- Binance API -> Producer/Ingestion Service.
- Producer -> Kafka.
- Kafka -> Flink.
- Flink -> Redis Sentinel.
- Flink -> InfluxDB.
- Kafka -> Spark.
- Spark -> Iceberg/MinIO.
- Trino -> Iceberg/MinIO.

AI and news:

- AI Service -> PostgreSQL: chat history, knowledge chunks, news.
- AI Service -> Provider Router/LLM Provider.
- News Service -> PostgreSQL: reads `news_articles`.

### Drawing Notes

The component diagram should show components and communication paths. Do not put detailed classes such as `CandleService` or `PromptBuilder` here unless drawing a subcomponent view of the backend or AI service.

## 4. 3-Node Docker Swarm Deployment Diagram

### Purpose

The deployment diagram describes where the system runs. For LMView, this diagram should follow the 3-node Docker Swarm architecture.

### Node 1: Manager / role=api

Containers/services:

- Nginx
- FastAPI
- PostgreSQL
- InfluxDB
- MinIO
- Kafka-1
- binance-ticker-ws
- binance-kline-rest
- binance-depth-trades-rest
- Prometheus
- Grafana
- Registry
- Certbot / DuckDNS
- Redis Sentinel-1

Role:

- Serves the frontend and backend API.
- Runs ingestion services.
- Stores relational data, warm time-series data, and object storage.
- Acts as one broker in the 3-broker Kafka cluster.

### Node 2: Worker / role=data

Containers/services:

- Zookeeper
- Kafka-2
- Schema Registry
- Redis Master
- Redis Sentinel-2
- Flink JobManager
- Flink TaskManager 1
- Spark Master
- Spark Worker 1
- Kafka Exporter

Role:

- Main streaming/data node.
- Hosts Redis Master for hot cache writes.
- Coordinates Flink and Spark.

### Node 3: Worker / role=compute

Containers/services:

- Kafka-3
- Redis Replica
- Redis Sentinel-3
- Flink TaskManager 2
- Spark Worker 2
- Trino
- Loki / Promtail
- Dagster, if optional orchestration is included

Role:

- Compute/analytics node.
- Runs Trino for Iceberg queries.
- Hosts Redis Replica for Sentinel failover.

### Infrastructure Relationships

- Kafka has 3 brokers, replication factor = 3, minISR = 2.
- Redis Master is on Node 2, Redis Replica is on Node 3, Sentinel quorum is 2/3.
- FastAPI on Node 1 reads Redis on Node 2, InfluxDB/PostgreSQL/MinIO on Node 1, and Trino on Node 3.
- Flink runs on Node 2 and Node 3, with checkpoints stored on MinIO.

## 5. ERD / Database Diagram

### Purpose

The ERD describes data stored in PostgreSQL. Do not mix Redis keys, Kafka topics, or Iceberg tables into the main ERD if you want the diagram to stay clean. Those can be documented in separate design tables.

### Tables

`users`:

- id
- email
- password_hash
- name
- role
- created_at
- updated_at

`user_settings`:

- id
- user_id
- preferences JSONB
- created_at
- updated_at

`ai_sessions`:

- id
- user_id
- title
- status
- created_at
- updated_at

`ai_messages`:

- id
- session_id
- role
- content
- metadata JSONB
- created_at

`ai_knowledge`:

- id
- title
- content
- source_url
- embedding vector(384)
- chunk_index
- created_at

`ai_feedback`:

- id
- message_id
- rating
- comment
- created_at

`news_articles`:

- id
- title
- content
- source
- url
- symbol
- published_at
- sentiment_score
- created_at

If Interact Mode is included:

- `tour_plans`
- `tour_step_logs`

### Relationships

- `users.id` 1-n `user_settings.user_id`.
- `users.id` 1-n `ai_sessions.user_id`.
- `ai_sessions.id` 1-n `ai_messages.session_id`.
- `ai_messages.id` 1-n `ai_feedback.message_id`.
- `ai_knowledge` is independent and queried by vector search.
- `news_articles` is independent or logically linked by the `symbol` field.

## 6. Class Diagram

### Purpose

The class diagram describes logical classes and business relationships. Do not draw Node 1/2/3, Kafka brokers, Redis Sentinel, or Docker services in the class diagram. Those belong in component and deployment diagrams.

### Market Classes

`Exchange`:

- code
- name
- status

`MarketSymbol`:

- symbol
- baseAsset
- quoteAsset
- exchange

`TickerSnapshot`:

- price
- volume24h
- changePercent
- high24h
- low24h
- timestamp

`Candle`:

- exchange
- symbol
- interval
- openTime
- closeTime
- open
- high
- low
- close
- volume

`TechnicalIndicator`:

- sma
- ema
- rsi
- macd
- macdSignal
- bollingerUpper
- bollingerMiddle
- bollingerLower

`OrderBook`:

- exchange
- symbol
- timestamp

`OrderBookLevel`:

- price
- quantity
- side

`Trade`:

- price
- quantity
- side
- tradeTime

### User/Auth Classes

`User`:

- id
- email
- name
- role
- status

`AuthSession`:

- id
- userId
- refreshTokenHash
- expiresAt

`UserSettings`:

- theme
- language
- defaultSymbol
- defaultTimeframe
- preferences

`Watchlist`:

- id
- userId
- symbols

### AI Classes

`AIChatSession`:

- id
- userId
- title
- status

`AIMessage`:

- id
- sessionId
- role
- content
- metadata

`ChartSnapshot`:

- symbol
- timeframe
- imageBase64
- visibleRange
- indicators

`KnowledgeChunk`:

- title
- content
- sourceUrl
- embedding

`Feedback`:

- rating
- comment

### News Classes

`NewsSource`:

- name
- url
- type

`NewsArticle`:

- title
- content
- url
- source
- symbol
- publishedAt

`NewsSentiment`:

- score
- label
- model

### Relationships

- `Exchange` 1-n `MarketSymbol`.
- `MarketSymbol` 1-n `TickerSnapshot`.
- `MarketSymbol` 1-n `Candle`.
- `MarketSymbol` 1-n `Trade`.
- `MarketSymbol` 0..1 `OrderBook`.
- `OrderBook` 1-n `OrderBookLevel`.
- `Candle` 0..1 `TechnicalIndicator`.
- `User` 1-n `AuthSession`.
- `User` 1-1 `UserSettings`.
- `User` 1-n `Watchlist`.
- `User` 1-n `AIChatSession`.
- `AIChatSession` 1-n `AIMessage`.
- `AIMessage` 0..1 `ChartSnapshot`.
- `AIMessage` 0..1 `Feedback`.
- `NewsSource` 1-n `NewsArticle`.
- `NewsArticle` 0..1 `NewsSentiment`.
- `NewsArticle` 0..n `MarketSymbol` through the `symbol` field.
- `AIMessage` depends on `KnowledgeChunk` and `NewsArticle` through RAG context.

## 7. Activity Diagram: Chart Loading and Data Fallback

### Purpose

This activity diagram describes how the backend serves chart data using the fallback order Redis -> InfluxDB -> Trino/Iceberg.

### Main Flow

1. User selects symbol/timeframe.
2. Frontend calls `/api/klines`.
3. FastAPI receives the request.
4. CandleService checks Redis.
5. Decision: does Redis have enough data?
6. If yes, return candles from Redis.
7. If no, CandleService queries InfluxDB.
8. Decision: does InfluxDB have enough data?
9. If yes, merge warm storage data.
10. If no, CandleService queries Trino/Iceberg.
11. Backend normalizes the response.
12. Frontend renders the chart.
13. Frontend opens WebSocket.
14. FastAPI reads Redis every 50ms.
15. Frontend updates the real-time candle.

### Decision Nodes

- Does Redis have enough candles?
- Does InfluxDB have enough data?
- Does Trino/Iceberg have enough historical data?
- Is the streaming candle closed?

### Recommended Swimlanes

- User
- Frontend
- FastAPI/CandleService
- Storage
- WebSocket

## 8. Sequence Diagram: Login

### Purpose

This sequence represents the `Register / Login` use case group.

### Lifelines

- User
- LoginForm
- authService
- AuthRouter
- AuthService
- PostgreSQL
- AuthContext

### Main Flow

1. User enters email and password.
2. LoginForm calls `authService.login(email, password)`.
3. authService sends `POST /api/auth/login`.
4. AuthRouter receives the request.
5. AuthRouter calls AuthService.
6. AuthService queries PostgreSQL by email.
7. PostgreSQL returns the user record.
8. AuthService verifies the password hash.
9. AuthService creates access token and refresh token.
10. AuthRouter returns the response to frontend.
11. authService returns token/user data to LoginForm.
12. AuthContext updates authentication state.
13. Frontend shows the main screen.

### Error Branches

Use an `alt` fragment:

- Email does not exist: return 401/404.
- Password is invalid: return 401.
- PostgreSQL fails: return 500 and show an error message.

## 9. Sequence Diagram: Real-Time Chart Viewing and Symbol/Timeframe Changes

### Purpose

This sequence represents the `View and Analyze Market Chart` use case group. It includes candle loading, symbol/timeframe changes, storage fallback, and WebSocket updates.

### Lifelines

- User
- Header/ChartPanel
- marketDataService
- KlinesRouter
- CandleService
- RedisRepository
- InfluxRepository
- TrinoRepository
- CandlestickChart
- WebSocketEndpoint

### Main Flow

1. User selects symbol and timeframe, for example `BTCUSDT`, `1m`.
2. Header/ChartPanel updates frontend state.
3. marketDataService calls `getKlines(exchange, symbol, interval)`.
4. KlinesRouter receives `GET /api/klines`.
5. KlinesRouter calls CandleService.
6. CandleService calls RedisRepository.
7. RedisRepository returns candles if available.
8. If Redis data is incomplete, CandleService calls InfluxRepository.
9. If InfluxDB data is incomplete, CandleService calls TrinoRepository.
10. CandleService normalizes and merges data.
11. KlinesRouter returns the response.
12. CandlestickChart calls `setData()`.
13. Frontend opens WebSocket `/api/stream/all?symbol=BTCUSDT`.
14. WebSocketEndpoint reads Redis in a 50ms loop.
15. WebSocketEndpoint sends updates to frontend.
16. CandlestickChart calls `update()` for the latest candle.

### Recommended Fragments

Use `alt`:

- Redis has enough data.
- Redis lacks data, use InfluxDB.
- Redis and InfluxDB both lack data, use Trino/Iceberg.

Use `opt`:

- User changes timeframe.
- User enables/disables technical indicators.
- WebSocket disconnects and reconnects.

## 10. Sequence Diagram: AI Assistant Question

### Purpose

This sequence represents the `Ask AI Assistant` use case group, including chart context, RAG, news context, provider routing, and chat persistence.

### Lifelines

- User
- AiAssistantPanel
- aiService
- AIRouter
- AIService/Orchestrator
- ScopeGate
- PromptBuilder
- RAGRetrieval
- NewsService
- ProviderRouter
- LLMProvider
- OutputGuard
- PostgreSQL

### Main Flow

1. User enters a question in AiAssistantPanel.
2. AiAssistantPanel collects chart context: symbol, timeframe, visible range, indicators, recent candles.
3. aiService sends `POST /api/ai/chat`.
4. AIRouter receives the request.
5. AIRouter calls AIService/Orchestrator.
6. ScopeGate checks whether the question belongs to the crypto/market domain.
7. PromptBuilder builds a prompt from the question, chart context, and chat history.
8. RAGRetrieval queries `ai_knowledge`.
9. If the question needs market news, NewsService loads relevant/latest `news_articles`.
10. PromptBuilder adds knowledge and news into the prompt context.
11. ProviderRouter chooses MockProvider or LiteLLMProvider.
12. LLMProvider generates the answer.
13. OutputGuard checks the response and adds disclaimer text if needed.
14. PostgreSQL stores the user message and assistant message.
15. AIRouter returns the final response.
16. AiAssistantPanel renders the markdown answer.

### Recommended Fragments

Use `alt`:

- Question is out of scope: ScopeGate rejects early.
- Provider fails: use fallback/mock if configured.

Use `opt`:

- Chart snapshot is included.
- Related news is included.
- User rates the answer after receiving it.

## 11. Sequence Diagram: Market News Reading

### Purpose

This sequence represents the `Read Market News` use case group. It balances the design because news is a user-facing feature and is also used as AI context.

### Lifelines

- User
- NewsPanel
- newsService
- NewsRouter
- NewsService
- PostgreSQL
- NewsCard

### Main Flow

1. User opens the News tab/panel.
2. NewsPanel calls `newsService.getLatestNews()`.
3. newsService sends `GET /api/news`.
4. NewsRouter receives the request.
5. NewsRouter calls NewsService.
6. NewsService queries PostgreSQL table `news_articles`.
7. PostgreSQL returns article rows.
8. NewsService sorts by latest `published_at`.
9. NewsRouter returns the response.
10. NewsPanel renders a list of NewsCard items.
11. User clicks a NewsCard.
12. NewsPanel shows article details or opens the external URL.

### Search/Filter Branch

Use `opt` or `alt`:

1. User enters a keyword or selects symbol/source/sentiment.
2. NewsPanel calls `GET /api/news?symbol=BTCUSDT&source=CoinDesk`.
3. NewsService filters by query parameters.
4. UI updates the filtered news list.

## 12. Balancing Use Cases and Sequence Diagrams

After the revision, each small use case does not need its own sequence diagram. Each sequence diagram represents one use case group:

| Sequence diagram | Covered use case group |
|---|---|
| Login | Register / Login, session management |
| Real-time chart viewing and symbol/timeframe changes | Chart viewing, symbol/timeframe changes, indicators, WebSocket updates |
| AI Assistant question | Question submission, chart context, RAG, news context, chat persistence, feedback |
| Market news reading | News list, news search/filter, news detail |

If a fifth sequence diagram is needed, choose `View order book/recent trades`, because it is an independent user action and demonstrates Redis hot-cache reads. If the thesis should stay concise, the four sequences above are enough.

## 13. Final Checklist

- Use cases are grouped, not listed as many tiny top-level actions.
- The class diagram does not contain containers, nodes, Kafka brokers, or Docker services.
- The component diagram includes all three Lambda paths: real-time, streaming, and batch.
- The deployment diagram follows the three roles: api, data, compute.
- The ERD focuses on PostgreSQL and does not mix Redis/Kafka into the same diagram.
- Every sequence diagram starts from a user action.
- Sequence diagrams do not describe internal crash/failover scenarios as user actions.
- News has at least one use case and one dedicated sequence diagram.
- The AI sequence includes chart context, RAG, and news context.
