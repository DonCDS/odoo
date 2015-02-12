{
    'name': 'Twitter Wall',
    'category': 'Website',
    'summary': 'Show Tweets',
    'version': '1.0',
    'description': """
Display Tweets from Wall
========================

 * Create wall
 * Verify with your twitter account
 * Make storify of your event
 * Comment on your tweet
 * Display live tweets in different kind of view with mode
 * You can moderate tweets just by posting or re-tweeting from twitter and twitter apps including mobile.
""",
    'author': 'Odoo SA',
    'depends': ['website'],
    'website': 'https://www.odoo.com',
    'data': [
        'views/twitter_wall.xml',
        'security/ir.model.access.csv',
        'data/twitter_data.xml',
    ],
    'installable': True,
}
