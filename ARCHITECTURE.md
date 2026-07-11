# 🏗️ EchoTrace AI — Architecture

## System Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        FE[Next.js Frontend]
        API_C[API Consumers]
    end

    subgraph Gateway["Gateway / Edge"]
        LB[Load Balancer]
        CDN[CDN / Static Assets]
    end

    subgraph Backend["Backend Layer"]
        FA[FastAPI Application]
        WS[WebSocket Manager]
        BG[Background Workers]
    end

    subgraph Services["Core Services"]
        AS[AI Service]
        ES[Evidence Service]
        IS[Investigation Service]
        RS[Report Service]
        NS[Notification Service]
        CS[Custody Service]
    end

    subgraph Storage["Data Layer"]
        PG[(PostgreSQL)]
        N4J[(Neo4j Graph)]
        RD[(Redis Cache)]
        FS[(Filesystem / S3)]
    end

    subgraph Monitoring["Observability"]
        PR[Prometheus]
        GF[Grafana]
        OT[OpenTelemetry]
        LG[Structured Logs]
    end

    Client --> LB
    LB --> FA
    LB --> WS
    FA --> Services
    Services --> Storage
    BG --> AS
    BG --> Storage
    FA --> Monitoring
    Services --> Monitoring
```

## Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant FA as FastAPI
    participant DB as PostgreSQL
    participant JWT as JWT Service

    C->>FA: POST /auth/login (email, password)
    FA->>DB: Query user by email
    DB-->>FA: User record
    FA->>JWT: Verify password (bcrypt)
    alt Success
        JWT-->>FA: Access token + Refresh token
        FA->>DB: Persist refresh token (hash)
        FA-->>C: 200 { access_token, refresh_token }
    else Failure
        FA-->>C: 401 Invalid credentials
    end

    Note over C,FA: Subsequent requests
    C->>FA: GET /evidences (Authorization: Bearer <token>)
    FA->>JWT: Decode and validate token
    alt Valid token
        JWT-->>FA: User payload
        FA->>DB: Query authorized data
        DB-->>FA: Result
        FA-->>C: 200 Response
    else Expired token
        FA-->>C: 401 Token expired
        C->>FA: POST /auth/refresh (refresh_token)
        FA->>DB: Validate refresh token rotation
        DB-->>FA: New token pair
        FA-->>C: 200 { new_access_token, new_refresh_token }
    end
```

## AI Processing Pipeline

```mermaid
sequenceDiagram
    participant U as User
    participant FA as FastAPI
    participant AS as AIService
    participant IG as Injection Guard
    participant AC as AICache
    participant P as AI Provider
    participant DB as PostgreSQL

    U->>FA: POST /ai/summarize (evidence_id)
    FA->>AS: summarize(evidence_id, user_id)
    AS->>IG: validate_input(text)
    IG-->>AS: Clean / Rejected
    AS->>DB: Create AIJob (status=running)
    AS->>AC: cache.get(cache_key)
    alt Cache Hit
        AC-->>AS: Cached result
        AS->>DB: Mark job completed (cached=True)
        AS-->>FA: AIJobResponse
        FA-->>U: 200 Cached result
    else Cache Miss
        AC-->>AS: None
        AS->>P: Call provider with timeout
        alt Success
            P-->>AS: LLM response
            AS->>AC: cache.set(result)
            AS->>DB: Mark job completed
            AS-->>FA: AIJobResponse
            FA-->>U: 200 Result
        else Timeout / Error
            P-->>AS: Exception
            AS->>DB: Mark job failed
            AS-->>FA: Error response
        end
    end

    alt Human Review
        U->>FA: GET /ai/suggestions (investigation_id)
        FA-->>U: Pending suggestions
        U->>FA: POST /ai/suggestions/{id}/approve
        FA->>DB: Persist suggested entity/relationship
        FA->>N4J: Sync graph
        FA-->>U: 200 Approved
    end
```

## Database Entity Relationships

```mermaid
erDiagram
    User ||--o{ WorkspaceMember : "belongs to"
    User ||--o{ Evidence : "creates"
    User ||--o{ Investigation : "creates"
    User ||--o{ RefreshToken : "owns"
    User ||--o{ PasswordResetToken : "owns"

    Organization ||--o{ Workspace : "contains"
    Workspace ||--o{ WorkspaceMember : "has members"
    Workspace ||--o{ Investigation : "holds"
    Workspace ||--o{ Project : "contains"

    Project ||--o{ Evidence : "contains"
    Evidence ||--o{ EvidenceVersion : "versions"
    Evidence ||--o{ EvidenceComment : "comments"
    Evidence ||--o{ EvidenceTag : "tagged with"
    Evidence ||--o{ ChainOfCustodyEvent : "audit trail"

    Investigation ||--o{ Entity : "has"
    Investigation ||--o{ Relationship : "connects"
    Investigation ||--o{ TimelineEvent : "timeline"
    Investigation ||--o{ EvidenceLink : "references"
    Investigation ||--o{ AISuggestion : "AI suggestions"
    Investigation ||--o{ AIJob : "AI jobs"

    Entity ||--o{ Relationship : "source"
    Entity ||--o{ Relationship : "target"
```

## Knowledge Graph Synchronization

```mermaid
flowchart LR
    A[Investigation Created/Updated] --> B[Sync Graph Triggered]
    B --> C{Neo4j Available?}
    C -->|Yes| D[Delete existing nodes]
    D --> E[Create Investigation node]
    E --> F[Batch create Entity nodes]
    F --> G[Batch create Relationship edges]
    G --> H[Graph ready for query]
    C -->|No| I[Log warning, skip sync]
    I --> J[Continue without graph]

    H --> K[GET /graph returns nodes + edges]
    K --> L[Frontend renders interactive graph]
```

## Background Job Processing

```mermaid
flowchart TD
    A[User requests AI operation] --> B[Create AIJob record]
    B --> C{Timeout?}
    C -->|Yes, within limits| D[Execute job in background task]
    C -->|No, async| E[Return job_id immediately]
    D --> F[Process with AIService]
    F --> G{Success?}
    G -->|Yes| H[Cache result, mark completed]
    G -->|Error| I[Mark failed, log error]
    G -->|Timeout| J[asyncio.wait_for fires]
    J --> K[Circuit breaker opens]
    K --> L[Retry after recovery timeout]

    H --> M[Return AIJobResponse]
    I --> M
```

## Deployment Architecture

```mermaid
graph TB
    subgraph Production["Production Environment"]
        subgraph Docker["Docker Compose / K8s"]
            PM[PostgreSQL 16]
            NM[Neo4j Enterprise]
            RM[Redis]
            BM[Backend FastAPI]
            FM[Frontend Next.js]
        end

        subgraph Monitoring["Monitoring Stack"]
            PR[Prometheus]
            GF[Grafana]
            OT[OpenTelemetry Collector]
            TM[Tempo]
            JG[Jaeger]
        end

        subgraph CI["CI/CD Pipeline"]
            GA[GitHub Actions]
            CQ[CodeQL]
            DB[Dependabot]
            TV[Trivy Scanner]
        end

        subgraph Registry["Container Registry"]
            GR[GitHub Container Registry]
        end

        CI -->|Build & Push| GR
        Docker -->|Pull Images| GR
        BM -->|Export metrics| PR
        FM -->|Export traces| OT
        BM -->|Send traces| OT
        OT -->|Forward| TM
        OT -->|Forward| JG
        PR -->|Visualize| GF
        TM -->|Visualize| GF
    end
```

## Data Flow — Evidence Upload & Verification

```mermaid
flowchart LR
    A[User uploads file] --> B[Size check]
    B --> C[Mime type validation]
    C --> D[Magic byte detection]
    D --> E{Mime allowed?}
    E -->|Yes| F[Compute SHA256]
    E -->|No| G[415 Unsupported Media Type]
    F --> H{Duplicate?}
    H -->|Yes| I[409 Conflict]
    H -->|No| J[Store file]
    J --> K[Create version record]
    K --> L[Custody chain entry]
    L --> M[Return enriched evidence]
```

---

*For detailed API documentation, refer to the Swagger UI at `/api/v1/docs`.*
*For operational runbooks, see `docs/runbooks/`.*
