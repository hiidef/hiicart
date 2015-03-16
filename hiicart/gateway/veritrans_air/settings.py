"""Settings for Veritrans Air gateway

**Required settings:**
 * *MERCHANT_ID*
 * *MERCHANTHASH*
 * *SESSION_ID*
 * *FINISH_PAYMENT_RETURN_URL*
 * *UNFINISH_PAYMENT_RETURN_URL*

**Optional settings:**
 * *ERROR_PAYMENT_RETURN_URL* -- URL to redirect to after an error occurs during checkouts (defaults: UNFINISH_PAYMENT_RETURN_URL)
 * *FINISH_PAYMENT_ACCESS_URL* -- URL to send IPN messages. [defualt: None (uses acct defaults)]

"""

SETTINGS = {
    'SETTLEMENT_TYPE': '00',
    'CARD_CAPTURE_FLAG': '1'
    }
