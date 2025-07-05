"""
Conversation states for the Samna Salta bot
"""

from telegram.ext import ConversationHandler

# Onboarding states (only these are actually used)
ONBOARDING_NAME = 1
ONBOARDING_PHONE = 2
ONBOARDING_DELIVERY_METHOD = 3
ONBOARDING_DELIVERY_ADDRESS = 4

# End conversation
END = ConversationHandler.END
