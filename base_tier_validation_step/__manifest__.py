{
    "name": "Base Tier Validation Step",
    "summary": "Step back to an earlier tier and require a confirmation "
    "before a tier can be validated",
    "version": "16.0.1.1.0",
    "category": "Tools",
    "author": "Aginix Technologies",
    "website": "https://github.com/madara1150/base_tier_validation_step",
    "license": "LGPL-3",
    "depends": ["base_tier_validation"],
    "data": [
        "security/tier_validation_step_security.xml",
        "security/ir.model.access.csv",
        "views/tier_definition_views.xml",
        "views/tier_review_views.xml",
        "wizards/tier_validation_step_wizard.xml",
        "templates/tier_validation_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "base_tier_validation_step/static/src/xml/*.xml",
        ],
    },
    "application": False,
    "installable": True,
}
