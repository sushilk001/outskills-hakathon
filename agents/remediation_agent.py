"""
Remediation Agent with RAG and MCP
Maps detected issues to fixes and provides rationale using knowledge base
Enhanced with MCP for real-time context from monitoring and infrastructure
"""
from typing import Dict, Any, List, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .base_agent import BaseAgent
from config import Config
import logging
import os

logger = logging.getLogger(__name__)

# Import MCP client if available
try:
    from mcp_client import MCPContextProvider
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP client not available")


class RemediationAgent(BaseAgent):
    """Agent responsible for finding remediation solutions using RAG"""
    
    def __init__(self, api_key: str = None, mcp_client=None):
        super().__init__(name="Remediation Agent", api_key=api_key)
        self.embeddings = self._initialize_embeddings()
        self.vector_store = None
        self._load_knowledge_base()
        
        # Initialize MCP client if enabled
        if MCP_AVAILABLE and Config.MCP_ENABLED:
            self.mcp_client = mcp_client or MCPContextProvider(enabled=True)
            logger.info("Remediation Agent: MCP enabled for enhanced context")
        else:
            self.mcp_client = None
    
    def _initialize_embeddings(self) -> Optional[HuggingFaceEmbeddings]:
        """Initialize embedding model"""
        try:
            return HuggingFaceEmbeddings(
                model_name=Config.EMBEDDING_MODEL,
                model_kwargs={'device': 'cpu'}
            )
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            return None
    
    def _load_knowledge_base(self):
        """Load or create knowledge base from documents"""
        vector_store_path = Config.VECTOR_STORE_DIR / "remediation_kb.faiss"
        
        try:
            # Try to load existing vector store
            if vector_store_path.exists():
                self.vector_store = FAISS.load_local(
                    str(Config.VECTOR_STORE_DIR / "remediation_kb"),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info("Loaded existing knowledge base")
            else:
                # Create from default knowledge
                self._create_default_knowledge_base()
                
        except Exception as e:
            logger.warning(f"Failed to load knowledge base: {e}")
            self._create_default_knowledge_base()
    
    def _create_default_knowledge_base(self):
        """Create a default knowledge base with common DevOps issues"""
        knowledge_docs = [
            {
                "issue": "Database Connection Timeout",
                "category": "database",
                "solution": "1. Check database server status\n2. Verify network connectivity\n3. Review connection pool settings\n4. Check for long-running queries\n5. Increase timeout settings if necessary",
                "rationale": "Connection timeouts typically occur due to network issues, overloaded database, or exhausted connection pools."
            },
            {
                "issue": "Out of Memory Error",
                "category": "memory",
                "solution": "1. Identify memory-intensive processes\n2. Review application memory leaks\n3. Increase heap size allocation\n4. Enable garbage collection logging\n5. Scale horizontally if needed",
                "rationale": "OOM errors indicate insufficient memory allocation or memory leaks. Monitoring and profiling are essential."
            },
            {
                "issue": "High CPU Usage",
                "category": "cpu",
                "solution": "1. Identify CPU-intensive processes\n2. Check for infinite loops or stuck threads\n3. Review algorithmic efficiency\n4. Enable CPU profiling\n5. Consider load balancing",
                "rationale": "High CPU usage can be caused by inefficient code, excessive load, or runaway processes."
            },
            {
                "issue": "Disk Space Full",
                "category": "disk",
                "solution": "1. Identify large files and logs\n2. Clean up old logs and temporary files\n3. Set up log rotation\n4. Expand disk capacity\n5. Archive old data",
                "rationale": "Running out of disk space can cause system instability. Regular cleanup and monitoring are crucial."
            },
            {
                "issue": "Network Connection Refused",
                "category": "network",
                "solution": "1. Verify service is running\n2. Check firewall rules\n3. Validate port configuration\n4. Review service health checks\n5. Check network connectivity",
                "rationale": "Connection refused errors indicate the service is not listening on the expected port or network issues exist."
            },
            {
                "issue": "Authentication Failed",
                "category": "security",
                "solution": "1. Verify credentials are correct\n2. Check token expiration\n3. Review permission settings\n4. Validate authentication service status\n5. Check certificate validity",
                "rationale": "Authentication failures can result from expired credentials, misconfigured permissions, or service outages."
            },
            {
                "issue": "Null Pointer Exception",
                "category": "application",
                "solution": "1. Review stack trace for exact location\n2. Add null checks in code\n3. Validate input parameters\n4. Review recent code changes\n5. Add defensive programming practices",
                "rationale": "Null pointer exceptions indicate missing data validation. Proper error handling prevents cascading failures."
            },
            {
                "issue": "HTTP 500 Internal Server Error",
                "category": "application",
                "solution": "1. Check application logs for exceptions\n2. Review recent deployments\n3. Verify configuration settings\n4. Check database connectivity\n5. Review upstream service dependencies",
                "rationale": "500 errors indicate server-side failures. Logs and monitoring provide insights into root causes."
            },
            {
                "issue": "HTTP 503 Service Unavailable",
                "category": "network",
                "solution": "1. Check service health status\n2. Review load balancer configuration\n3. Verify autoscaling settings\n4. Check for resource exhaustion\n5. Review circuit breaker status",
                "rationale": "503 errors indicate temporary unavailability. Often related to overload or maintenance."
            },
            {
                "issue": "DNS Resolution Failed",
                "category": "network",
                "solution": "1. Verify DNS server status\n2. Check DNS configuration\n3. Review /etc/hosts file\n4. Test with nslookup/dig\n5. Check network connectivity to DNS",
                "rationale": "DNS failures prevent service discovery. Proper DNS configuration is critical for distributed systems."
            }
        ]
        
        # Convert to documents
        texts = []
        for doc in knowledge_docs:
            text = f"""Issue: {doc['issue']}
Category: {doc['category']}
Solution:
{doc['solution']}

Rationale: {doc['rationale']}
"""
            texts.append(text)
        
        # Create vector store
        if self.embeddings and texts:
            try:
                self.vector_store = FAISS.from_texts(
                    texts,
                    self.embeddings
                )
                # Save for future use
                self.vector_store.save_local(
                    str(Config.VECTOR_STORE_DIR / "remediation_kb")
                )
                logger.info("Created default knowledge base")
            except Exception as e:
                logger.error(f"Failed to create knowledge base: {e}")
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find remediation solutions for detected issues
        
        Args:
            input_data: Dict with 'issues_found' from LogReaderAgent
            
        Returns:
            Dict with remediation recommendations
        """
        self.status = "processing"
        self.log_action("Starting remediation analysis")
        
        try:
            issues = input_data.get("issues_found", [])
            
            if not issues:
                return {
                    "success": True,
                    "agent": self.name,
                    "message": "No issues to remediate",
                    "remediations": []
                }
            
            # Find remediations for each issue
            remediations = []
            for issue in issues[:10]:  # Limit to top 10 critical issues
                remediation = await self._find_remediation(issue)
                if remediation:
                    remediations.append(remediation)
            
            self.status = "completed"
            self.log_action(f"Generated {len(remediations)} remediation plans")
            
            return {
                "success": True,
                "agent": self.name,
                "total_issues": len(issues),
                "remediations": remediations,
                "execution_log": self.execution_log
            }
            
        except Exception as e:
            self.status = "failed"
            self.log_action(f"Error: {str(e)}")
            logger.error(f"{self.name} failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    async def _find_remediation(self, issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find remediation for a specific issue using RAG + MCP context"""
        try:
            # Create query from issue
            query = f"{issue['category']} {issue['severity']} {issue['message']}"
            
            # Retrieve relevant knowledge from RAG
            relevant_docs = []
            if self.vector_store:
                try:
                    relevant_docs = self.vector_store.similarity_search(
                        query,
                        k=Config.TOP_K_RESULTS
                    )
                except Exception as e:
                    logger.warning(f"Vector search failed: {e}")
            
            # Get MCP context (real-time metrics, infrastructure state, etc.)
            mcp_context = ""
            mcp_data = {}
            if self.mcp_client:
                try:
                    # Query metrics based on issue category
                    if "database" in issue['category'].lower() or "connection" in issue['message'].lower():
                        metrics = await self.mcp_client.get_metrics("database_connections", "5m")
                        infra_state = await self.mcp_client.get_infrastructure_state("pod", {
                            "name": "database-pod",
                            "namespace": "production"
                        })
                        mcp_data["metrics"] = metrics
                        mcp_data["infrastructure"] = infra_state
                    elif "cpu" in issue['message'].lower() or "memory" in issue['message'].lower():
                        metrics = await self.mcp_client.get_metrics("cpu_usage", "5m")
                        mcp_data["metrics"] = metrics
                    elif "error" in issue['message'].lower():
                        metrics = await self.mcp_client.get_metrics("error_rate", "5m")
                        health = await self.mcp_client.get_service_health("api-service")
                        mcp_data["metrics"] = metrics
                        mcp_data["health"] = health
                    
                    # Get recent similar incidents
                    recent_incidents = await self.mcp_client.get_recent_incidents(issue['category'], 24)
                    if recent_incidents:
                        mcp_data["recent_incidents"] = recent_incidents
                    
                    # Format MCP context for prompt
                    if mcp_data:
                        mcp_context = "\n\n**Real-Time Context (MCP):**\n"
                        if "metrics" in mcp_data and mcp_data["metrics"]:
                            m = mcp_data["metrics"]
                            mcp_context += f"- Current Metrics: {m.get('metric', 'N/A')} = {m.get('value', 'N/A')} {m.get('unit', '')} ({m.get('status', 'unknown')} status)\n"
                            mcp_context += f"  Trend: {m.get('trend', 'unknown')}, Message: {m.get('message', '')}\n"
                        if "infrastructure" in mcp_data and mcp_data["infrastructure"]:
                            i = mcp_data["infrastructure"]
                            mcp_context += f"- Infrastructure State: {i.get('status', 'unknown')} - {i.get('message', '')}\n"
                            if "restarts" in i:
                                mcp_context += f"  Restarts: {i.get('restarts', 0)}, Resource Usage: {i.get('memory_usage', 'N/A')}\n"
                        if "recent_incidents" in mcp_data and mcp_data["recent_incidents"]:
                            incidents = mcp_data["recent_incidents"]
                            mcp_context += f"- Recent Similar Incidents: Found {len(incidents)} similar incidents\n"
                            for inc in incidents[:2]:
                                mcp_context += f"  • {inc.get('key', 'N/A')}: {inc.get('summary', '')} - Resolution: {inc.get('resolution', 'N/A')}\n"
                except Exception as e:
                    logger.warning(f"MCP context retrieval failed: {e}")
                    mcp_context = ""
            
            # Generate remediation using LLM with enhanced context
            if self.llm:
                context = "\n\n".join([doc.page_content for doc in relevant_docs]) if relevant_docs else "No specific knowledge available."
                
                prompt = f"""You are a DevOps expert. Given this incident, relevant knowledge, and real-time context, provide a clear remediation plan.

**Incident Details:**
- Severity: {issue['severity']}
- Category: {issue['category']}
- Message: {issue['message']}
- Timestamp: {issue.get('timestamp', 'Unknown')}

**Relevant Knowledge (RAG):**
{context}
{mcp_context}

Provide:
1. **Root Cause**: Brief explanation (1-2 sentences) - use MCP context if available
2. **Immediate Action**: What to do right now (3-5 steps) - prioritize based on real-time metrics
3. **Long-term Fix**: Prevent recurrence (2-3 points)
4. **Priority**: Critical/High/Medium/Low
5. **Confidence**: High/Medium/Low (based on available context)

Format as clear, actionable steps. If MCP context is available, reference it in your analysis."""

                response = self.llm.invoke(prompt)
                
                # Determine confidence based on available context
                confidence = "medium"
                if mcp_data and relevant_docs:
                    confidence = "high"
                elif mcp_data or relevant_docs:
                    confidence = "medium-high"
                
                return {
                    "issue": issue,
                    "remediation_plan": response.content.strip(),
                    "knowledge_sources": len(relevant_docs),
                    "mcp_context_used": bool(mcp_data),
                    "mcp_data": mcp_data if mcp_data else None,
                    "confidence": confidence
                }
            else:
                # Fallback without LLM
                return {
                    "issue": issue,
                    "remediation_plan": f"Manual investigation required for {issue['category']} issue: {issue['message'][:100]}",
                    "knowledge_sources": 0,
                    "confidence": "low"
                }
                
        except Exception as e:
            logger.error(f"Remediation failed for issue: {e}")
            return None

