# ruff: noqa
import os
import sys
import re
import json
import datetime
from google.adk import Workflow, Context, Event
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.events import RequestInput
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.workflow import node
from google.genai import types

from app.config import config

# Setup paths for local MCP server
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_SERVER_PATH = os.path.join(CURRENT_DIR, "mcp_server.py")

# Create local MCP Toolset
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[MCP_SERVER_PATH]
        )
    )
)

# Sub-Agent 1: Resource Finder Agent
resource_finder = Agent(
    name="resource_finder",
    model=Gemini(
        model=config.model,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are a helpful educational resource finder. 
Your goal is to find free, high-quality online courses, textbooks, lectures, and practice problems 
for students based on their subjects and grade level.
Always provide clickable URLs where possible. Use your search_internet_resources tool to find resource links.""",
    tools=[mcp_toolset],
)

# Sub-Agent 2: Study Scheduler Agent
study_scheduler = Agent(
    name="study_scheduler",
    model=Gemini(
        model=config.model,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are an expert academic scheduler. 
Your goal is to build personalized, highly structured, and realistic study plans for students.
Break study schedules down by week and day, allocating realistic time blocks.
You can get the current date using the get_current_calendar tool and log/save study schedules using log_study_schedule tool.""",
    tools=[mcp_toolset],
)

# Security checkpoint node
@node
def security_checkpoint(ctx: Context, node_input: str):
    timestamp = datetime.datetime.utcnow().isoformat()
    
    # 1. PII Scrubbing
    scrubbed = node_input
    if config.pii_redaction_enabled:
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        scrubbed = re.sub(email_pattern, "[REDACTED_EMAIL]", scrubbed)
        scrubbed = re.sub(phone_pattern, "[REDACTED_PHONE]", scrubbed)
    
    # 2. Prompt Injection Detection
    injection_found = False
    if config.injection_detection_enabled:
        injection_keywords = ["ignore instructions", "ignore previous instructions", "system override", "jailbreak", "you must now"]
        for kw in injection_keywords:
            if kw in node_input.lower():
                injection_found = True
                break
                
    # 3. Domain Specific Rules (Academic Integrity Check)
    cheating_found = False
    cheating_keywords = ["cheat on exam", "exam answers", "do my homework", "cheat on test", "homework solver"]
    for kw in cheating_keywords:
        if kw in node_input.lower():
            cheating_found = True
            break
            
    # Audit log
    audit_data = {
        "timestamp": timestamp,
        "pii_redacted": scrubbed != node_input,
        "prompt_injection_detected": injection_found,
        "academic_integrity_violation": cheating_found,
        "severity": "INFO"
    }
    
    if injection_found:
        audit_data["severity"] = "CRITICAL"
        print(json.dumps(audit_data))
        return Event(route="SECURITY_EVENT", output="Security Block: Prompt injection detected.")
        
    if cheating_found:
        audit_data["severity"] = "WARNING"
        print(json.dumps(audit_data))
        return Event(route="SECURITY_EVENT", output="Security Block: Requests for cheating or exam answers are not allowed. Please ask for study concepts or schedule assistance instead.")
        
    print(json.dumps(audit_data))
    
    # Store clean input in context state
    ctx.state["clean_input"] = scrubbed
    ctx.state["approved_schedule"] = False
    
    return Event(route="PROCEED", output=scrubbed)

# Security error handler node
@node
def security_error_node(ctx: Context, node_input: str):
    return f"Access Denied: {node_input}"

# Orchestrator Agent
orchestrator = Agent(
    name="orchestrator",
    model=Gemini(
        model=config.model,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are the EduGuide main coordinator. 
Your role is to understand the user's study needs. 
If the user wants resource materials, delegate to the resource_finder tool.
If the user wants a study plan or schedule, delegate to the study_scheduler tool.
Always answer using information gathered from the tools. If a study schedule is produced, make sure it is detailed.""",
    tools=[
        AgentTool(agent=resource_finder, skip_summarization=True),
        AgentTool(agent=study_scheduler, skip_summarization=True),
    ],
)

# Router node to check if the output requires human approval
@node
def router_node(ctx: Context, node_input: str):
    # Check if this is an actual study schedule breakdown, not just a description of capabilities
    has_schedule_keywords = "schedule" in node_input.lower() or "study plan" in node_input.lower()
    
    # Use regex word boundaries so that "today", "yesterday", etc. do not trigger a false schedule match.
    has_breakdown = bool(re.search(r'\b(day|week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', node_input.lower()))
    is_schedule = has_schedule_keywords and has_breakdown
    
    already_approved = ctx.state.get("approved_schedule", False)
    
    if is_schedule and not already_approved:
        ctx.state["proposed_schedule"] = node_input
        return Event(route="NEEDS_APPROVAL", output=node_input)
    else:
        return Event(route="AUTO_APPROVE", output=node_input)

# Human approval node (yields RequestInput)
@node(rerun_on_resume=False)
def human_approval(ctx: Context, node_input: str):
    feedback = yield RequestInput(
        message=f"Please review the proposed study schedule:\n\n{node_input}\n\nDo you approve this schedule? (Type 'yes' to approve, or describe any changes you want):"
    )
    
    if str(feedback).lower().strip() in ["yes", "approve", "y"]:
        ctx.state["approved_schedule"] = True
        yield Event(route="APPROVED", output=node_input)
    else:
        ctx.state["approved_schedule"] = False
        refinement_prompt = f"The user requested changes to the study schedule:\n'{feedback}'\nPlease revise the schedule accordingly."
        yield Event(route="REJECTED", output=refinement_prompt)

# Final output formatter node
@node
def final_output(ctx: Context, node_input: str):
    approved = ctx.state.get("approved_schedule", False)
    header = "🎓 [APPROVED STUDY PLAN] 🎓\n\n" if approved else ""
    return f"{header}{node_input}"

# Define the Workflow Graph
root_agent = Workflow(
    name="eduguide_workflow",
    edges=[
        ("START", security_checkpoint),
        (security_checkpoint, {
            "SECURITY_EVENT": security_error_node,
            "PROCEED": orchestrator
        }),
        (orchestrator, router_node),
        (router_node, {
            "NEEDS_APPROVAL": human_approval,
            "AUTO_APPROVE": final_output
        }),
        (human_approval, {
            "APPROVED": final_output,
            "REJECTED": orchestrator
        })
    ]
)

app = App(
    root_agent=root_agent,
    name="app",
)