"""Social housing policy definitions seed data."""

from __future__ import annotations

from yourai.policy.schemas import (
    ComplianceCriterion,
    CreatePolicyDefinition,
    LegislationReference,
    ScoringCriterion,
)

# Social Housing Policy Definitions for UK housing associations
# Organized by group: Health & Safety, Tenant Services, Asset Management, Governance

SOCIAL_HOUSING_DEFINITIONS = [
    # ========================================================================
    # Group 1: Health & Safety
    # ========================================================================
    CreatePolicyDefinition(
        name="Health & Safety Policy",
        uri="health-and-safety-policy",
        description="Covers workplace safety, risk assessments, incident reporting, and compliance with health and safety legislation",
        is_required=True,
        review_cycle="annual",
        name_variants=[
            "Workplace Safety Policy",
            "H&S Policy",
            "Occupational Health and Safety Policy",
        ],
        required_sections=[
            "Policy Statement",
            "Scope and Objectives",
            "Responsibilities",
            "Risk Assessment",
            "Incident Reporting",
            "Training and Competence",
            "Review and Monitoring",
        ],
        scoring_criteria=[
            ScoringCriterion(
                criterion="Risk Assessment Process",
                green_threshold="Comprehensive risk assessment framework with regular reviews (at least annually)",
                amber_threshold="Basic risk assessment process with some gaps in coverage or review frequency",
                red_threshold="No documented risk assessment process or severely outdated assessments",
            ),
            ScoringCriterion(
                criterion="Incident Reporting and Investigation",
                green_threshold="Clear reporting procedures with root cause analysis and corrective actions documented",
                amber_threshold="Basic incident reporting present but lacking investigation or follow-up procedures",
                red_threshold="No incident reporting system or no evidence of investigations",
            ),
            ScoringCriterion(
                criterion="Compliance with Legislation",
                green_threshold="Policy explicitly references and addresses all relevant H&S legislation with recent updates",
                amber_threshold="Policy references key legislation but missing some requirements or outdated",
                red_threshold="No legislative references or policy predates major regulatory changes",
            ),
        ],
        compliance_criteria=[
            ComplianceCriterion(
                name="Health and Safety at Work etc. Act 1974 Compliance",
                priority="high",
                description="Policy must address employer duties under HSWA 1974 s.2 (duty to employees) and s.3 (duty to others)",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Risk Assessment Documentation",
                priority="high",
                description="Documented risk assessments for all work activities as per Management of Health and Safety at Work Regulations 1999",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="RIDDOR Reporting Procedures",
                priority="high",
                description="Clear procedures for reporting injuries, diseases and dangerous occurrences under RIDDOR 2013",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Competency and Training",
                priority="medium",
                description="Framework for ensuring staff competence and provision of adequate training",
                criteria_type="recommended",
            ),
        ],
        legislation_references=[
            LegislationReference(
                act_name="Health and Safety at Work etc. Act 1974",
                section="s.2",
                notes="Employer's duty to employees",
            ),
            LegislationReference(
                act_name="Management of Health and Safety at Work Regulations 1999",
                section="reg.3",
                notes="Risk assessment requirement",
            ),
            LegislationReference(
                act_name="Reporting of Injuries, Diseases and Dangerous Occurrences Regulations 2013",
                notes="RIDDOR reporting requirements",
            ),
        ],
    ),
    CreatePolicyDefinition(
        name="Fire Safety Policy",
        uri="fire-safety-policy",
        description="Fire prevention, detection, evacuation procedures, and compliance with fire safety legislation for residential properties",
        is_required=True,
        review_cycle="annual",
        name_variants=[
            "Fire Prevention Policy",
            "Fire Safety Management Policy",
        ],
        required_sections=[
            "Policy Statement",
            "Scope",
            "Fire Risk Assessment",
            "Fire Safety Measures",
            "Emergency Procedures",
            "Training and Drills",
            "Maintenance and Testing",
            "Review",
        ],
        scoring_criteria=[
            ScoringCriterion(
                criterion="Fire Risk Assessments",
                green_threshold="Fire risk assessments completed for all properties with annual reviews and action plans",
                amber_threshold="Fire risk assessments present for most properties but some overdue or incomplete",
                red_threshold="No fire risk assessments or assessments more than 3 years out of date",
            ),
            ScoringCriterion(
                criterion="Compliance with Regulatory Reform Order",
                green_threshold="Policy explicitly addresses all RRO 2005 requirements with documented compliance evidence",
                amber_threshold="Policy references RRO 2005 but lacks detail on some requirements",
                red_threshold="No reference to RRO 2005 or policy predates the regulation",
            ),
            ScoringCriterion(
                criterion="Resident Communication",
                green_threshold="Clear procedures for communicating fire safety information to residents with evidence of implementation",
                amber_threshold="Basic communication procedures but limited evidence of regular implementation",
                red_threshold="No documented resident communication procedures",
            ),
        ],
        compliance_criteria=[
            ComplianceCriterion(
                name="Regulatory Reform (Fire Safety) Order 2005 Compliance",
                priority="high",
                description="Policy must address responsible person duties under RRO 2005",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Fire Risk Assessment Process",
                priority="high",
                description="Documented fire risk assessments for all buildings and common areas",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Emergency Evacuation Plans",
                priority="high",
                description="Personal Emergency Evacuation Plans (PEEPs) for vulnerable residents",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Fire Safety Equipment Maintenance",
                priority="medium",
                description="Regular testing and maintenance schedules for fire alarms, extinguishers, and emergency lighting",
                criteria_type="recommended",
            ),
        ],
        legislation_references=[
            LegislationReference(
                act_name="Regulatory Reform (Fire Safety) Order 2005",
                section="art.9",
                notes="Fire risk assessment requirement",
            ),
            LegislationReference(
                act_name="Building Safety Act 2022",
                notes="Enhanced fire safety requirements for higher-risk buildings",
            ),
        ],
    ),
    CreatePolicyDefinition(
        name="Asbestos Management Policy",
        uri="asbestos-management-policy",
        description="Management of asbestos-containing materials in properties, including surveys, registers, and safe removal procedures",
        is_required=True,
        review_cycle="annual",
        name_variants=[
            "Asbestos Policy",
            "Asbestos Control Policy",
        ],
        required_sections=[
            "Policy Statement",
            "Legal Framework",
            "Asbestos Register",
            "Risk Assessment",
            "Management Plan",
            "Contractor Requirements",
            "Training",
            "Review and Monitoring",
        ],
        scoring_criteria=[
            ScoringCriterion(
                criterion="Asbestos Register Completeness",
                green_threshold="Comprehensive asbestos register for all properties with survey dates within last 5 years",
                amber_threshold="Asbestos register present but some properties missing surveys or surveys overdue",
                red_threshold="No asbestos register or majority of properties unsurveyed",
            ),
            ScoringCriterion(
                criterion="Compliance with Control of Asbestos Regulations",
                green_threshold="Policy addresses all CAR 2012 requirements with documented duty to manage",
                amber_threshold="Policy references CAR 2012 but lacks detail on duty to manage or risk assessment",
                red_threshold="No reference to current asbestos regulations",
            ),
        ],
        compliance_criteria=[
            ComplianceCriterion(
                name="Control of Asbestos Regulations 2012 Compliance",
                priority="high",
                description="Policy must address duty to manage asbestos under CAR 2012 reg.4",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Asbestos Register Maintenance",
                priority="high",
                description="Up-to-date asbestos register for all non-domestic premises and common areas",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Contractor Licensing Verification",
                priority="high",
                description="Procedures for ensuring only licensed contractors work with asbestos",
                criteria_type="mandatory",
            ),
        ],
        legislation_references=[
            LegislationReference(
                act_name="Control of Asbestos Regulations 2012",
                section="reg.4",
                notes="Duty to manage asbestos",
            ),
            LegislationReference(
                act_name="Health and Safety at Work etc. Act 1974",
                section="s.3",
                notes="Duty to persons not in employment",
            ),
        ],
    ),
    # ========================================================================
    # Group 2: Tenant Services
    # ========================================================================
    CreatePolicyDefinition(
        name="Tenancy Management Policy",
        uri="tenancy-management-policy",
        description="Tenancy allocation, management, termination, and tenant rights and responsibilities",
        is_required=True,
        review_cycle="annual",
        name_variants=[
            "Lettings Policy",
            "Allocations and Lettings Policy",
            "Tenancy Policy",
        ],
        required_sections=[
            "Policy Statement",
            "Allocations Framework",
            "Tenancy Types",
            "Tenancy Agreements",
            "Rent Setting",
            "Tenancy Support",
            "Tenancy Termination",
            "Appeals Process",
        ],
        scoring_criteria=[
            ScoringCriterion(
                criterion="Compliance with Regulator Standards",
                green_threshold="Policy explicitly addresses all Tenancy Standard requirements with evidence of compliance",
                amber_threshold="Policy references Tenancy Standard but lacks detail on some requirements",
                red_threshold="No reference to RSH Tenancy Standard or significant gaps",
            ),
            ScoringCriterion(
                criterion="Tenant Engagement",
                green_threshold="Clear procedures for tenant involvement in policy development and review",
                amber_threshold="Basic tenant consultation mentioned but limited evidence of implementation",
                red_threshold="No tenant engagement provisions",
            ),
        ],
        compliance_criteria=[
            ComplianceCriterion(
                name="Regulator of Social Housing Tenancy Standard Compliance",
                priority="high",
                description="Policy must meet all requirements of the RSH Tenancy Standard",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Allocations Transparency",
                priority="high",
                description="Clear, fair, and transparent allocations framework published to applicants",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Tenancy Agreement Clarity",
                priority="medium",
                description="Tenancy agreements in plain English explaining rights and responsibilities",
                criteria_type="recommended",
            ),
        ],
        legislation_references=[
            LegislationReference(
                act_name="Housing Act 1985",
                section="s.81",
                notes="Secure tenancies",
            ),
            LegislationReference(
                act_name="Housing Act 1996",
                section="Part VII",
                notes="Allocation of housing",
            ),
            LegislationReference(
                act_name="Localism Act 2011",
                notes="Flexible tenancies and allocations reforms",
            ),
        ],
    ),
    CreatePolicyDefinition(
        name="Anti-Social Behaviour Policy",
        uri="anti-social-behaviour-policy",
        description="Managing and responding to anti-social behaviour by tenants and residents, including enforcement action",
        is_required=True,
        review_cycle="annual",
        name_variants=[
            "ASB Policy",
            "Neighbour Disputes Policy",
            "Community Safety Policy",
        ],
        required_sections=[
            "Policy Statement",
            "Definition of ASB",
            "Reporting Procedures",
            "Risk Assessment",
            "Case Management",
            "Enforcement Action",
            "Support for Victims",
            "Partnership Working",
        ],
        scoring_criteria=[
            ScoringCriterion(
                criterion="ASB Case Management",
                green_threshold="Clear case management procedures with risk assessment, action plans, and victim support",
                amber_threshold="Basic case management process but lacking risk assessment or victim support detail",
                red_threshold="No documented case management procedures",
            ),
            ScoringCriterion(
                criterion="Legislative Compliance",
                green_threshold="Policy addresses ASB Crime and Policing Act 2014 tools and powers with usage guidance",
                amber_threshold="Policy references ASBCPA 2014 but lacks detail on available tools",
                red_threshold="No reference to current ASB legislation",
            ),
        ],
        compliance_criteria=[
            ComplianceCriterion(
                name="Anti-social Behaviour, Crime and Policing Act 2014 Compliance",
                priority="high",
                description="Policy must reference available tools under ASBCPA 2014 (Community Protection Notices, etc.)",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Multi-Agency Partnership",
                priority="medium",
                description="Procedures for working with police, local authority, and other partners",
                criteria_type="recommended",
            ),
            ComplianceCriterion(
                name="Victim Support Framework",
                priority="high",
                description="Clear support procedures for victims and witnesses of ASB",
                criteria_type="mandatory",
            ),
        ],
        legislation_references=[
            LegislationReference(
                act_name="Anti-social Behaviour, Crime and Policing Act 2014",
                notes="ASB tools and powers",
            ),
            LegislationReference(
                act_name="Housing Act 1996",
                section="s.153A-E",
                notes="Anti-social behaviour grounds for possession",
            ),
        ],
    ),
    CreatePolicyDefinition(
        name="Complaints Policy",
        uri="complaints-policy",
        description="Handling and resolving tenant complaints, including complaints procedure and escalation to Housing Ombudsman",
        is_required=True,
        review_cycle="annual",
        name_variants=[
            "Complaints Handling Policy",
            "Complaints Procedure",
        ],
        required_sections=[
            "Policy Statement",
            "Scope",
            "Complaints Definition",
            "Two-Stage Process",
            "Timescales",
            "Remedies",
            "Housing Ombudsman Escalation",
            "Learning from Complaints",
        ],
        scoring_criteria=[
            ScoringCriterion(
                criterion="Compliance with Housing Ombudsman Code",
                green_threshold="Policy fully compliant with Housing Ombudsman Complaint Handling Code with evidence of self-assessment",
                amber_threshold="Policy mostly compliant but some gaps identified in self-assessment",
                red_threshold="Policy not compliant with Complaint Handling Code or no self-assessment completed",
            ),
            ScoringCriterion(
                criterion="Learning and Improvement",
                green_threshold="Clear procedures for learning from complaints with evidence of service improvements",
                amber_threshold="Basic learning framework but limited evidence of implementation",
                red_threshold="No documented learning or improvement process",
            ),
        ],
        compliance_criteria=[
            ComplianceCriterion(
                name="Housing Ombudsman Complaint Handling Code Compliance",
                priority="high",
                description="Policy must comply with all mandatory requirements of the Complaint Handling Code",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Two-Stage Process",
                priority="high",
                description="Clear two-stage complaints procedure as required by the Code",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Response Timescales",
                priority="high",
                description="Stage 1: 10 working days, Stage 2: 20 working days as per the Code",
                criteria_type="mandatory",
            ),
        ],
        legislation_references=[
            LegislationReference(
                act_name="Housing Ombudsman Complaint Handling Code",
                notes="Mandatory requirements for complaint handling",
            ),
            LegislationReference(
                act_name="Localism Act 2011",
                section="s.180-184",
                notes="Housing Ombudsman powers",
            ),
        ],
    ),
    # ========================================================================
    # Group 3: Asset Management
    # ========================================================================
    CreatePolicyDefinition(
        name="Repairs and Maintenance Policy",
        uri="repairs-maintenance-policy",
        description="Responsive repairs, emergency repairs, tenant responsibilities, and repair standards",
        is_required=True,
        review_cycle="annual",
        name_variants=[
            "Repairs Policy",
            "Maintenance Policy",
            "Responsive Repairs Policy",
        ],
        required_sections=[
            "Policy Statement",
            "Repair Responsibilities",
            "Emergency Repairs",
            "Routine Repairs",
            "Repair Timescales",
            "Right to Repair",
            "Quality Standards",
            "Tenant Responsibilities",
        ],
        scoring_criteria=[
            ScoringCriterion(
                criterion="Repair Timescales",
                green_threshold="Clear timescales for all repair categories with performance monitoring against targets",
                amber_threshold="Basic timescales defined but limited monitoring or inconsistent performance",
                red_threshold="No defined timescales or no performance monitoring",
            ),
            ScoringCriterion(
                criterion="Decent Homes Standard Compliance",
                green_threshold="Policy explicitly addresses Decent Homes Standard with compliance evidence",
                amber_threshold="Policy references Decent Homes but lacks detail or compliance data",
                red_threshold="No reference to Decent Homes Standard",
            ),
        ],
        compliance_criteria=[
            ComplianceCriterion(
                name="Landlord and Tenant Act 1985 Compliance",
                priority="high",
                description="Policy must address repairing obligations under LTA 1985 s.11",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Right to Repair Scheme",
                priority="medium",
                description="Implementation of Right to Repair scheme for qualifying repairs",
                criteria_type="recommended",
            ),
            ComplianceCriterion(
                name="Decent Homes Standard",
                priority="high",
                description="Commitment to maintaining properties to Decent Homes Standard",
                criteria_type="mandatory",
            ),
        ],
        legislation_references=[
            LegislationReference(
                act_name="Landlord and Tenant Act 1985",
                section="s.11",
                notes="Repairing obligations",
            ),
            LegislationReference(
                act_name="Housing Act 2004",
                section="Part 1",
                notes="Housing Health and Safety Rating System (HHSRS)",
            ),
        ],
    ),
    CreatePolicyDefinition(
        name="Planned Maintenance Policy",
        uri="planned-maintenance-policy",
        description="Long-term maintenance programme, cyclical works, and major works including component replacement",
        is_required=False,
        review_cycle="annual",
        name_variants=[
            "Asset Management Policy",
            "Long-Term Maintenance Policy",
            "Cyclical Works Policy",
        ],
        required_sections=[
            "Policy Statement",
            "Asset Management Strategy",
            "Stock Condition Surveys",
            "Planned Works Programme",
            "Component Lifecycles",
            "Tenant Consultation",
            "Procurement",
            "Performance Monitoring",
        ],
        scoring_criteria=[
            ScoringCriterion(
                criterion="Asset Management Planning",
                green_threshold="Comprehensive asset management strategy with 30-year financial plan and stock condition data",
                amber_threshold="Basic asset management plan but limited stock condition data or financial planning",
                red_threshold="No asset management strategy or severely outdated",
            ),
            ScoringCriterion(
                criterion="Tenant Consultation on Major Works",
                green_threshold="Clear consultation procedures for major works with evidence of tenant engagement",
                amber_threshold="Basic consultation process but limited evidence of implementation",
                red_threshold="No documented consultation procedures",
            ),
        ],
        compliance_criteria=[
            ComplianceCriterion(
                name="Section 20 Consultation Compliance",
                priority="high",
                description="Policy must address statutory consultation requirements under LTA 1985 s.20",
                criteria_type="mandatory",
            ),
            ComplianceCriterion(
                name="Stock Condition Data",
                priority="medium",
                description="Up-to-date stock condition surveys informing planned works programme",
                criteria_type="recommended",
            ),
        ],
        legislation_references=[
            LegislationReference(
                act_name="Landlord and Tenant Act 1985",
                section="s.20",
                notes="Consultation requirements for qualifying works and agreements",
            ),
        ],
    ),
]
