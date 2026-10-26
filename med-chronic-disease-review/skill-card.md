## Description: <br>
门诊慢病审核（糖尿病/高血压）。输入 OCR 结果数组 JSON，由内部医疗大模型输出审核结论与原因（原始 JSON + 自然语言结论）。 <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
[unisound-llm](https://clawhub.ai/user/unisound-llm) <br>

### License/Terms of Use: <br>
MIT-0 <br>


## Use Case: <br>
Claims-review teams and developers use this skill to review diabetes or hypertension chronic-disease outpatient insurance materials from OCR text or supported document inputs. It returns a structured decision and concise natural-language reasoning for human review. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Sensitive medical OCR data may be sent to the configured medical LLM endpoint. <br>
Mitigation: Use only in an approved environment, verify redaction before model calls, and confirm that policy permits sending the data to the configured endpoint with the provided app key. <br>
Risk: Review outputs may be written under ../runs and could contain medical or claim-review details. <br>
Mitigation: Set controlled output paths, restrict access to generated JSON and text files, and remove retained outputs according to the deployment policy. <br>
Risk: The security evidence reports conflicting privacy and storage claims. <br>
Mitigation: Confirm the actual redaction, storage, and retention behavior before using the skill with patient records. <br>


## Reference(s): <br>
- [ClawHub skill page](https://clawhub.ai/unisound-llm/skills/med-chronic-disease-review) <br>
- [Publisher profile](https://clawhub.ai/user/unisound-llm) <br>
- [Configured medical LLM endpoint](https://maas-api.hivoice.cn/v1/chat/completions) <br>


## Skill Output: <br>
**Output Type(s):** [text, json, files, shell commands] <br>
**Output Format:** [Structured JSON response plus natural-language text summary files] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Outputs include final_decision and reasoning; dry-run mode emits a placeholder decision without calling the model.] <br>

## Skill Version(s): <br>
1.0.2 (source: server release evidence) <br>

## Ethical Considerations: <br>
Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment. <br>
