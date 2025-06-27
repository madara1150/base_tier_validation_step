# -*- coding: utf-8 -*-
{
    'name': 'Base_tier_validation_step',
    'version': '16.0.1.0.0',
    'summary': """ Base_tier_validation_step Summary """,
    'author': 'Aginix Technologies',
    'website': '',
    'category': '',
    'depends': ['base', 'web', 'base_tier_validation'],
    "data": [
        "security/ir.model.access.csv",
        "views/tier_definition_views.xml",
        "views/tier_review_views.xml",
        "wizards/tier_validation_step_wizard.xml",
        "templates/tier_validation_templates.xml"
    ],
    'assets': {
              'web.assets_backend': [
                  'base_tier_validation_step/static/src/**/*'
              ],
          },
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
