# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'HiiCart.shipping_option_name'
        db.alter_column(u'hiicart_hiicart', 'shipping_option_name', self.gf('django.db.models.fields.CharField')(max_length=75, null=True))


    def backwards(self, orm):
        
        # Changing field 'HiiCart.shipping_option_name'
        db.alter_column(u'hiicart_hiicart', 'shipping_option_name', self.gf('django.db.models.fields.CharField')(max_length=50, null=True))


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2014, 2, 3, 22, 42, 39, 54576)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2014, 2, 3, 22, 42, 39, 53768)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'hiicart.hiicart': {
            'Meta': {'object_name': 'HiiCart'},
            '_cart_state': ('django.db.models.fields.CharField', [], {'default': "'OPEN'", 'max_length': '16', 'db_index': 'True'}),
            '_cart_uuid': ('django.db.models.fields.CharField', [], {'max_length': '36', 'db_index': 'True'}),
            '_sub_total': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '18', 'decimal_places': '2', 'blank': 'True'}),
            '_total': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '2'}),
            'bill_city': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'bill_country': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '2'}),
            'bill_email': ('django.db.models.fields.EmailField', [], {'default': "''", 'max_length': '255'}),
            'bill_first_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'bill_last_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'bill_phone': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '30'}),
            'bill_postal_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '30'}),
            'bill_state': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'bill_street1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '80'}),
            'bill_street2': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '80'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'custom_id': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'discount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '18', 'decimal_places': '2', 'blank': 'True'}),
            'failure_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True'}),
            'fulfilled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'gateway': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'ship_city': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'ship_country': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '2'}),
            'ship_email': ('django.db.models.fields.EmailField', [], {'default': "''", 'max_length': '255'}),
            'ship_first_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'ship_last_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'ship_phone': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '30'}),
            'ship_postal_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '30'}),
            'ship_state': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'ship_street1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '80'}),
            'ship_street2': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '80'}),
            'shipping': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '18', 'decimal_places': '2', 'blank': 'True'}),
            'shipping_option_name': ('django.db.models.fields.CharField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'success_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True'}),
            'tax': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '18', 'decimal_places': '2', 'blank': 'True'}),
            'tax_country': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'tax_rate': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '6', 'decimal_places': '5', 'blank': 'True'}),
            'tax_region': ('django.db.models.fields.CharField', [], {'max_length': '127', 'null': 'True', 'blank': 'True'}),
            'thankyou': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'hiicart.lineitem': {
            'Meta': {'object_name': 'LineItem'},
            '_sub_total': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '10'}),
            '_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '18', 'decimal_places': '2'}),
            'cart': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['hiicart.HiiCart']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'digital_description': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'discount': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '18', 'decimal_places': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'quantity': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'sku': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '255', 'db_index': 'True'}),
            'unit_price': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '10'})
        },
        u'hiicart.note': {
            'Meta': {'object_name': 'Note'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        u'hiicart.payment': {
            'Meta': {'object_name': 'Payment'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '2'}),
            'cart': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'payments'", 'to': u"orm['hiicart.HiiCart']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'gateway': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'transaction_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '45', 'null': 'True', 'blank': 'True'})
        },
        u'hiicart.paymentresponse': {
            'Meta': {'object_name': 'PaymentResponse'},
            'cart': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'payment_results'", 'to': u"orm['hiicart.HiiCart']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'response_code': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'response_text': ('django.db.models.fields.TextField', [], {})
        },
        u'hiicart.recurringlineitem': {
            'Meta': {'object_name': 'RecurringLineItem'},
            '_sub_total': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '10'}),
            '_total': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '18', 'decimal_places': '2'}),
            'cart': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['hiicart.HiiCart']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'digital_description': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'discount': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '18', 'decimal_places': '10'}),
            'duration': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'duration_unit': ('django.db.models.fields.CharField', [], {'default': "'DAY'", 'max_length': '5'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'payment_token': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True'}),
            'quantity': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'recurring_price': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '18', 'decimal_places': '2'}),
            'recurring_shipping': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '18', 'decimal_places': '2'}),
            'recurring_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'recurring_times': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'sku': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '255', 'db_index': 'True'}),
            'trial': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'trial_length': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'trial_price': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '18', 'decimal_places': '2'}),
            'trial_times': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'})
        }
    }

    complete_apps = ['hiicart']
