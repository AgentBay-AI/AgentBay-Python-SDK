"""
AI Agent Tracking SDK - Hybrid Session Management

This package provides comprehensive tracking capabilities for AI Agents with 
a hybrid session management system that combines local lightweight caching 
with backend persistence.

Agent Operations Tracker:
- Agent registration and status management  
- Activity logging and monitoring
- Real-time agent operations tracking

Agent Performance Tracker:
- Conversation quality metrics
- Success rate calculations  
- Response time tracking
- Failed session management
- Hybrid session tracking with 10h local TTL + 20h backend persistence
- Seamless session resumption across crashes and restarts

Hybrid Session Model:
- Local cache: Lightweight session details with 10-hour sliding TTL
- Backend persistence: Full session data with 20-hour TTL from last activity
- Automatic fallback: If local cache expires but backend has session, seamlessly resume
- Crash resilience: Sessions survive SDK restarts through backend persistence
- Single source of truth: Backend maintains authoritative session state

Key Features:
- Secure API communication
- Async/sync support
- Sliding TTL for active session management
- Seamless session resumption
- Backend fallback and recovery
- Thread-safe operations
- Comprehensive logging
- Rich session analytics

Session Lifecycle:
1. start_conversation() → Creates session in local cache + backend
2. Session active → Sliding TTL resets on each access (local cache)
3. Local TTL expires → Automatic backend retrieval if still within 20h
4. Session resumption → Seamless continuation with context
5. Backend TTL expires → Session permanently expired
"""

from .AgentOper import (
    AgentOperationsTracker,
    AgentStatus,
    APIResponse,
    SecureLogger,
    SecureAPIClient,
    AgentRegistrationData,
    AgentStatusData,
    ActivityLogData
)

from .AgentPerform import (
    AgentPerformanceTracker,
    ConversationQuality,
    ConversationStartData,
    ConversationEndData,
    FailedSessionData,
    SessionRetrievalQuery,
    SessionInfo,
    QueuedEvent,
    MessageData,
    ConversationHistoryData,
    PerformanceMetrics
)

from .LLMtracker import LLMTracker

# Import security add-on components (optional)
try:
    from .security import (
        SecurityWrapper,
        SecurityManager,
        SecurityFlags,
        SecurityMetricEvent,
        TamperDetectionEvent,
        UnclosedSessionInfo,
        OTELTracer,
        detect_pii,
        scan_metadata_for_pii,
        create_secure_performance_tracker,
        create_secure_operations_tracker
    )
    _SECURITY_AVAILABLE = True
except ImportError:
    _SECURITY_AVAILABLE = False

# Import compliance add-on components (optional)
try:
    from .compliance import (
        ComplianceWrapper,
        ComplianceManager,
        ComplianceFlags,
        PolicyViolation,
        UserAcknowledgment,
        ComplianceAuditEntry,
        PHIDetector,
        GDPRDetector,
        create_compliance_tracker,
        create_compliance_operations_tracker,
        create_smart_compliance_tracker
    )
    _COMPLIANCE_AVAILABLE = True
except ImportError:
    _COMPLIANCE_AVAILABLE = False

__version__ = "1.2.1"
__all__ = [
    # Agent Operations
    "AgentOperationsTracker",
    "AgentRegistrationData",
    "AgentStatusData", 
    "ActivityLogData",
    
    # Agent Performance - Hybrid Session Management
    "AgentPerformanceTracker",
    "ConversationStartData",
    "ConversationEndData",
    "FailedSessionData",
    "SessionRetrievalQuery",
    "SessionInfo",
    "QueuedEvent",
    "ConversationQuality",
    "MessageData",
    "ConversationHistoryData",
    "PerformanceMetrics",
    
    # LLM Usage Tracking
    "LLMTracker",
    
    # API Response
    "APIResponse",
    
    # Security
    "SecureLogger",
    "SecureAPIClient"
]

# Add security exports if available
if _SECURITY_AVAILABLE:
    __all__.extend([
        "SecurityWrapper",
        "SecurityManager", 
        "SecurityFlags",
        "SecurityMetricEvent",
        "TamperDetectionEvent",
        "UnclosedSessionInfo",
        "OTELTracer",
        "detect_pii",
        "scan_metadata_for_pii",
        "create_secure_performance_tracker",
        "create_secure_operations_tracker"
    ])

# Add compliance exports if available
if _COMPLIANCE_AVAILABLE:
    __all__.extend([
        "ComplianceWrapper",
        "ComplianceManager",
        "ComplianceFlags",
        "PolicyViolation",
        "UserAcknowledgment",
        "ComplianceAuditEntry",
        "PHIDetector",
        "GDPRDetector",
        "create_compliance_tracker",
        "create_compliance_operations_tracker",
        "create_smart_compliance_tracker"
    ])

# Note: Session tracking uses a hybrid model.
# The SDK keeps a lightweight local cache with sliding TTL and relies on backend persistence for resilience. 