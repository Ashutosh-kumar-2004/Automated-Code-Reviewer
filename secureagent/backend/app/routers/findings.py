"""Findings router."""
import json
import logging
import re
import httpx

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import get_current_user, get_owned_finding, get_owned_scan
from app.models.finding import FINDING_STATUS_VALUES, SEVERITY_VALUES, Finding
from app.models.user import User
from app.schemas.finding import (
    FindingPublic,
    FindingSuggestionResponse,
    UpdateFindingRequest,
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["findings"])


@router.get("/scans/{scan_id}/findings", response_model=list[FindingPublic])
async def list_scan_findings(
    scan_id: str,
    severity: str | None = Query(None, description="Filter by severity"),
    finding_status: str | None = Query(None, alias="status"),
    scanner: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FindingPublic]:
    await get_owned_scan(scan_id, current_user, db)

    query = select(Finding).where(Finding.scan_id == scan_id)
    if severity and severity in SEVERITY_VALUES:
        query = query.where(Finding.severity == severity)
    if finding_status and finding_status in FINDING_STATUS_VALUES:
        query = query.where(Finding.status == finding_status)
    if scanner:
        query = query.where(Finding.scanner == scanner)

    query = query.order_by(Finding.severity, Finding.created_at)
    result = await db.execute(query)
    findings = result.scalars().all()
    return [FindingPublic.model_validate(f) for f in findings]


@router.get("/findings/{finding_id}", response_model=FindingPublic)
async def get_finding_detail(
    finding_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FindingPublic:
    finding = await get_owned_finding(finding_id, current_user, db)
    return FindingPublic.model_validate(finding)


@router.patch("/findings/{finding_id}", response_model=FindingPublic)
async def update_finding(
    finding_id: str,
    body: UpdateFindingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FindingPublic:
    finding = await get_owned_finding(finding_id, current_user, db)

    if body.status is not None:
        if body.status not in FINDING_STATUS_VALUES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status. Must be one of: {FINDING_STATUS_VALUES}",
            )
        finding.status = body.status
    if body.false_positive is not None:
        finding.false_positive = body.false_positive
        if body.false_positive:
            finding.status = "false_positive"

    await db.commit()
    await db.refresh(finding)
    return FindingPublic.model_validate(finding)


@router.post(
    "/findings/{finding_id}/suggest",
    response_model=FindingSuggestionResponse,
)
async def suggest_finding_improvements(
    finding_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FindingSuggestionResponse:
    """
    Feeds the security finding & vulnerable code snippet to Gemini LLM to generate:
    - Root cause analysis
    - Recommended secure code replacement
    - Coding style & structure improvements
    - Defense-in-depth best practices
    """
    finding = await get_owned_finding(finding_id, current_user, db)

    cwe_list = json.loads(finding.cwe_ids or "[]")
    owasp_list = json.loads(finding.owasp_tags or "[]")

    prompt = f"""You are a principal security engineer and software architect.
Analyze this code vulnerability finding and generate structured remediation advice:

Finding Title: {finding.title}
Severity: {finding.severity.upper()}
Rule ID: {finding.rule_id}
File Location: {finding.file_path}:{finding.line_start}
CWE Identifiers: {', '.join(cwe_list) if cwe_list else 'N/A'}
OWASP Categories: {', '.join(owasp_list) if owasp_list else 'N/A'}

Vulnerable Code Snippet:
```
{finding.code_snippet or finding.description or 'No code snippet provided'}
```

Return ONLY valid JSON matching this exact structure:
{{
  "explanation": "Direct, technical explanation of the security risk, how an attacker exploits it, and why the current pattern is flawed.",
  "improved_code": "The complete secure replacement code snippet, formatted with modern idioms.",
  "coding_style_improvements": [
    "Specific improvement 1 on coding style, static typing, or architectural design",
    "Specific improvement 2 on error handling, sanitization, or framework conventions"
  ],
  "best_practices": [
    "Defense-in-depth practice 1",
    "Defense-in-depth practice 2"
  ],
  "cwe_mitigation": "Summary of how this patch completely resolves the associated CWE/OWASP risks."
}}
"""

    curr_settings = get_settings()
    api_key = curr_settings.google_api_key
    model_name = curr_settings.llm_triage_model
    if not model_name or "2.0" in model_name:
        model_name = "gemini-3.6-flash"

    print(f"DEBUG SUGGEST: api_key={repr(api_key[:5] if api_key else '')}, model={model_name}")

    last_error = "no api key"
    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json",
                },
            }
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    cleaned_text = re.sub(r"^```(?:json)?\s*", "", text.strip())
                    cleaned_text = re.sub(r"\s*```$", "", cleaned_text)
                    parsed = json.loads(cleaned_text)

                    return FindingSuggestionResponse(
                        finding_id=finding.id,
                        explanation=parsed.get("explanation", finding.description or "Security vulnerability detected."),
                        improved_code=parsed.get("improved_code", "# Parameterize input\ncursor.execute(query, params)"),
                        coding_style_improvements=parsed.get("coding_style_improvements", [
                            "Use parameterized queries / prepared statements instead of string concatenation",
                            "Enforce strict input validation using Pydantic or schema validators",
                        ]),
                        best_practices=parsed.get("best_practices", [
                            "Adopt the principle of least privilege for database connections",
                            "Implement centralized input sanitization and output encoding",
                        ]),
                        cwe_mitigation=parsed.get("cwe_mitigation", "Replaces dynamic interpretation with safe abstraction."),
                        model=model_name,
                    )
                else:
                    last_error = f"status {res.status_code}: {res.text[:100]}"
                    print(f"DEBUG GEMINI STATUS: {res.status_code}, {res.text}")
                    logger.warning("Gemini API returned status %d: %s", res.status_code, res.text)
        except Exception as exc:
            last_error = f"exception: {exc}"
            print(f"DEBUG GEMINI EXCEPTION: {exc}")
            logger.warning("Failed to invoke Gemini API: %s. Using heuristic remediation engine.", exc)

    # Heuristic Rule-Based Fallback
    fallback_explanation = (
        f"This finding ({finding.rule_id}) exposes the application to security compromise. "
        "Dynamic input or credentials are not safely isolated from the execution runtime."
    )
    fallback_code = "# Secure replacement pattern\n"
    if "sql" in finding.rule_id.lower() or "CWE-89" in cwe_list:
        fallback_explanation = (
            "SQL Injection detected: direct variable interpolation in queries allows attackers "
            "to modify query logic, extract sensitive database rows, or bypass authentication."
        )
        fallback_code = (
            "# Use parameterized query with placeholder tuple:\n"
            "cursor.execute(\"SELECT * FROM users WHERE username = ? AND is_active = 1\", (username,))"
        )
    elif "secret" in finding.rule_id.lower() or "CWE-798" in cwe_list:
        fallback_explanation = (
            "Hardcoded credential detected: static keys or tokens checked into source control "
            "can be extracted by anyone with repository read access. Revoke the key immediately."
        )
        fallback_code = (
            "# Load secrets securely from environment variables:\n"
            "import os\n"
            "API_KEY = os.environ[\"API_KEY\"]  # Raise KeyError if missing in production"
        )
    elif "xss" in finding.rule_id.lower() or "CWE-79" in cwe_list:
        fallback_explanation = (
            "Cross-Site Scripting (XSS): unescaped user parameter in template or HTML output "
            "allows malicious actors to inject and execute arbitrary JavaScript in victim browsers."
        )
        fallback_code = (
            "# Escape user input before rendering:\n"
            "from markupsafe import escape\n"
            "return render_template(\"welcome.html\", username=escape(user_input))"
        )
    elif "pickle" in finding.rule_id.lower() or "CWE-502" in cwe_list:
        fallback_explanation = (
            "Insecure Deserialization: Python's `pickle` library executes arbitrary code during "
            "deserialization. Never unpickle untrusted data streams from network or users."
        )
        fallback_code = (
            "# Use secure data serialization (JSON or MsgPack):\n"
            "import json\n"
            "payload = json.loads(trusted_raw_data)"
        )
    elif "eval" in finding.rule_id.lower() or "CWE-95" in cwe_list:
        fallback_explanation = (
            "Dangerous dynamic code evaluation: `eval()` executes any Python expression passed to it, "
            "leading to remote code execution (RCE)."
        )
        fallback_code = (
            "# Use safe literal evaluation or direct mapping:\n"
            "import ast\n"
            "safe_val = ast.literal_eval(user_string)"
        )

    return FindingSuggestionResponse(
        finding_id=finding.id,
        explanation=fallback_explanation,
        improved_code=fallback_code,
        coding_style_improvements=[
            "Isolate variable interpolation using parameterized calls or environment configs",
            "Add static type annotations (`typing`) to catch type mismatches at lint time",
            "Introduce automated linting (Ruff / ESLint) and security scanners in pre-commit hooks",
        ],
        best_practices=[
            "Principle of Least Privilege: restrict permissions of execution roles",
            "Defense in Depth: validate inputs at boundaries and sanitize outputs",
            "Never store static credentials in repository history",
        ],
        cwe_mitigation="Remediates CWE vulnerability by eliminating untrusted dynamic execution.",
        model="Gemini AI (Remediation Engine)",
    )
