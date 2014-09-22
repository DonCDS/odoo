{
    'name': 'Twitter Wall',
    'category': 'Website',
    'summary': 'Show tweet',
    'version': '1.0',
    'description': """
Display tweets from users wall
=====================================
You can create and display as multiple walls for your concurrent sessions, management of wall is as easy is working with Twitter, You can moderate tweets just by posting or re-tweeting from and twitter apps including mobile.
""",
    'author': 'OpenERP SA',
    'depends': ['website'],
    'data': [
        'views/twitter_wall_conf.xml',
        'views/twitter_wall.xml',
        'security/ir.model.access.csv'
     ],
    'demo': [],
    'qweb': [],
    'installable': True,
}