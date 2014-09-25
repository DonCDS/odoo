# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import json
import urllib
import thread
import urllib2
import datetime

import openerp
from openerp import api
from openerp.osv import osv
from openerp.osv import fields
from twitter_stream import WallListener, Stream
from openerp.addons.website_twitter_wall.controllers.oauth import oauth

stream_pool = {
    
}

class TwitterWall(osv.osv):
    _name = "website.twitter.wall"

    _columns = {
        'name': fields.char('Wall Name'),
        'description': fields.text('Description'),
        'tweet_ids': fields.one2many('website.twitter.wall.tweet', 'wall_id', 'Tweets'),
        'website_id': fields.many2one('website', 'Website'),
        're_tweet': fields.boolean('Include Re-Tweet ?'),
        'state': fields.selection([('not_streaming', 'Draft'), ('streaming', 'In Progress'), ('story', 'Story')], string="State"),
        'website_published': fields.boolean('Visible in Website'),

        'user_id': fields.many2one('res.users', 'Created User'),

        'twitter_access_token': fields.char('Twitter Access Token key', help="Twitter Access Token Key"),
        'twitter_access_token_secret': fields.char('Twitter Access Token secret', help="Twitter Access Token Secret"),

        'image': fields.binary('Image'),
        'image_thumb': fields.binary('Thumbnail')
    }

    _defaults = {
        'website_id': 1,
        'state': 'not_streaming',
        'website_published': True,
        'user_id': lambda obj, cr, uid, ctx=None: uid,
    }

    def check(self, counter):
        result = not counter
        return result

    def get_api_keys(self):
        twitter_api_key = 'mQP4B4GIFo0bjGW4VB1wMxNJ3'
        twitter_api_secret = 'XrRKiqONjENN55PMW8xxPx8XOL6eKitt53Ks8OS9oeEZD9aEBf'
        return twitter_api_key, twitter_api_secret

    def start_incoming_tweets(self, cr, uid, ids, context=None):
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        for wall in self.browse(cr, uid, ids, context=context):
            def func(stream, user_ids):
                return stream.filter(follow=user_ids)

            if stream_pool.get(wall.id):
                return True
        
            if wall.twitter_access_token and wall.twitter_access_token_secret:
                twitter_api_key, twitter_api_secret = self.get_api_keys()
                auth = oauth(twitter_api_key, twitter_api_secret)

                listner = WallListener(base_url, wall)

                auth.set_access_token(wall.twitter_access_token, wall.twitter_access_token_secret)
                stream = stream_pool.get(wall.id, False)
                if not stream:
                    stream = Stream(auth, listner)
                stream_pool[wall.id] = stream

                user_ids = auth.get_authorise_user_id()
                thread.start_new_thread(func, (stream, [user_ids], ))

        self.write(cr, uid, ids, {'state': 'streaming'}, context=context)
        return True

    #TODO: to check, may be useful to place this image in to website module
    def crop_image(self, data, type='top', ratio=False, thumbnail_ratio=None, image_format="PNG"):
        """ Used for cropping image and create thumbnail
            :param data: base64 data of image.
            :param type: Used for cropping position possible
                Possible Values : 'top', 'center', 'bottom'
            :param ratio: Cropping ratio
                e.g for (4,3), (16,9), (16,10) etc
                send ratio(1,1) to generate square image
            :param thumbnail_ratio: It is size reduce ratio for thumbnail
                e.g. thumbnail_ratio=2 will reduce your 500x500 image converted in to 250x250
            :param image_format: return image format PNG,JPEG etc
        """
        
        image = Image.open(cStringIO.StringIO(data.decode('base64')))
        output = io.BytesIO()
        w, h = image.size
        new_h = h
        new_w = w

        if ratio:
            w_ratio, h_ratio = ratio
            new_h = (w * h_ratio) / w_ratio
            new_w = w
            if new_h > h:
                new_h = h
                new_w = (h * w_ratio) / h_ratio

        if type == "top":
            cropped_image = image.crop((0, 0, new_w, new_h))
            cropped_image.save(output,format=image_format)
        elif type == "center":
            cropped_image = image.crop(((w - new_w)/2, (h - new_h)/2, (w + new_w)/2, (h + new_h)/2))
            cropped_image.save(output,format=image_format)
        elif type == "bottom":
            cropped_image = image.crop((0, h - new_h, new_w, h))
            cropped_image.save(output,format=image_format)
        else:
            raise ValueError('ERROR: invalid value for crop_type')
        if thumbnail_ratio:
            thumb_image = Image.open(cStringIO.StringIO(output.getvalue()))
            thumb_image.thumbnail((new_w/thumbnail_ratio, new_h/thumbnail_ratio), Image.ANTIALIAS)
            output = io.BytesIO()
            thumb_image.save(output, image_format)
        return output.getvalue().encode('base64')


    def create(self, cr, uid, values, context):
        if values.get('image'):
            image_thumb = self.crop_image(values['image'], thumbnail_ratio=4)
            image = self.crop_image(values['image'])
            values.update({
                'image_thumb': image_thumb,
                'image': image
            })

        wall_id = super(TwitterWall, self).create(cr, uid, values, context)
        return wall_id

    def stop_incoming_tweets(self, cr, uid, ids, context=None):
        for wall in ids:
            stream_pool.get(wall).disconnect()
        self.write(cr, uid, ids, {'state': 'not_streaming'}, context=context)
        return True

    def create_tweets(self, cr, uid, ids, vals, context=None):
        tweet = self.pool.get('website.twitter.wall.tweet')
        tweet_val = tweet._process_tweet(cr, uid, ids, vals)
        tweet_id = tweet.create(cr, uid, tweet_val)
        return tweet_id

    def unlink(self, cr, uid, ids, context=None):
        twitter_obj = self.pool.get('website.twitter.wall.tweet')
        for id in ids:
            tweet_ids = twitter_obj.search(cr, uid, [('wall_id', '=', id)])
            twitter_obj.unlink(cr, uid, tweet_ids, context=context)
        return super(TwitterWall, self).unlink(cr, uid, ids, context=context)

class WebsiteTwitterTweet(osv.osv):
    _name = "website.twitter.wall.tweet"

    _columns = {
        'wall_id': fields.many2one('website.twitter.wall', 'Wall'),
        'html_description': fields.html('Tweet'),
        'tweet_id': fields.char('Tweet Id', size=256),
        'tweet_json': fields.text('Tweet Json Data'),
        'published_date': fields.datetime('Publish on')
    }

    _sql_constraints = [
        ('tweet_uniq', 'unique (wall_id, tweet_id)', 'Duplicate tweet in wall is not allowed !')
    ]

    def _process_tweet(self, cr, uid, wall_id, tweet, context=None):
        card_url = "https://api.twitter.com/1/statuses/oembed.json?id=%s&omit_script=true" % (tweet.get('id'))
        req = urllib2.Request(card_url, None, {'Content-Type': 'application/json'})
        response = urllib2.urlopen(req)
        data = response.read()
        cardtweet = json.loads(data)

        vals = {
            'html_description': cardtweet.get('html', False),
            'tweet_json': tweet,
            'tweet_id': tweet.get('id'),
            'published_date': datetime.datetime.now(),
            'wall_id': wall_id
        }
        return vals