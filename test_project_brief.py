from workflow_contract import ProjectBrief, create_project_brief


payload = {
    "company_name": " Alpha Studio ",
    "target_customer": " Malaysian SMEs ",
    "core_service": " AI websites ",
    "region": " Malaysia ",
    "language": " Chinese ",
    "cta": " Book a consultation ",
    "contact": " WhatsApp: +60123456789 ",
}

brief = create_project_brief(payload)

assert isinstance(brief, ProjectBrief)
assert brief.company_name == "Alpha Studio"
assert brief.contact == "WhatsApp: +60123456789"

try:
    create_project_brief({**payload, "company_name": " ", "cta": None})
except ValueError as error:
    assert str(error) == "Invalid project brief fields: company_name, cta"
else:
    raise AssertionError("Invalid fields must raise ValueError")

print("Project-brief tests passed.")
