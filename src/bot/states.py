"""
Conversation states for the Samna Salta bot
"""

from telegram.ext import ConversationHandler


# Onboarding states
ONBOARDING_NAME = 1
ONBOARDING_PHONE = 2
ONBOARDING_DELIVERY_METHOD = 3
ONBOARDING_DELIVERY_ADDRESS = 4

# Menu states
MENU_MAIN = 10
MENU_PRODUCT = 11
MENU_PRODUCT_OPTIONS = 12
MENU_PRODUCT_OPTIONS_2 = 13

# Cart states
CART_VIEW = 20
CART_CONFIRMATION = 21
CART_EDIT_DETAILS = 22

# Admin states
ADMIN_MAIN = 30
ADMIN_ADD_PRODUCT = 31
ADMIN_EDIT_PRODUCT = 32
ADMIN_DELETE_PRODUCT = 33

# End conversation
END = ConversationHandler.END 