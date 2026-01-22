import re
import json
from typing import List, Tuple, Optional, Any
from aiogram.types import Message, InlineKeyboardMarkup, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

class ResponseSplitter:
    MAX_BUBBLES_PER_BATCH = 3 
    MAX_CHARS_PER_BUBBLE = 280 

    @staticmethod
    def extract_buttons(text: str) -> Tuple[str, Optional[str]]:
        """
        Extracts <<BUTTONS: ...>> and returns (clean_text, button_definition_string).
        """
        button_match = re.search(r'<<BUTTONS:(.*?)>>', text, re.DOTALL | re.IGNORECASE)
        if button_match:
            button_str = button_match.group(1).strip()
            clean_text = text.replace(button_match.group(0), "").strip()
            return clean_text, button_str
        return text.strip(), None

    @staticmethod
    def create_keyboard_from_def(button_def: str) -> InlineKeyboardMarkup:
        if not button_def: return None
        builder = InlineKeyboardBuilder()
        labels = [l.strip() for l in re.split(r'[,|]', button_def) if l.strip()]
        for label in labels:
            # Simple callback: "smart_act:{label}"
            # If label is "Opción 1", callback is "smart_act:Opción 1"
            clean_label = label[:30]
            builder.button(text=label, callback_data=f"smart_act:{clean_label}")
        builder.adjust(2)
        return builder.as_markup()

    @staticmethod
    def split_text(text: str) -> List[str]:
        raw_paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        bubbles = []
        for p in raw_paragraphs:
            if len(p) <= ResponseSplitter.MAX_CHARS_PER_BUBBLE:
                bubbles.append(p)
            else:
                current_bubble = ""
                sentences = re.split(r'(?<=[.?!])\s+', p)
                for s in sentences:
                    if len(current_bubble) + len(s) < ResponseSplitter.MAX_CHARS_PER_BUBBLE:
                        current_bubble += s + " "
                    else:
                        if current_bubble: bubbles.append(current_bubble.strip())
                        current_bubble = s + " "
                if current_bubble: bubbles.append(current_bubble.strip())
        return bubbles

    @staticmethod
    def get_batch(bubbles: List[str]) -> Tuple[List[str], List[str]]:
        return bubbles[:ResponseSplitter.MAX_BUBBLES_PER_BATCH], bubbles[ResponseSplitter.MAX_BUBBLES_PER_BATCH:]

async def send_smart_response(message_or_callback: Any, text: str, state: FSMContext) -> None:
    """
    Main entry point for sending responses with Consolidacion Rules.
    Handles extraction, splitting, and initial sending.
    """
    # 1. Cleaning & Extraction
    clean_text, button_def = ResponseSplitter.extract_buttons(text)
    
    # 2. Splitting
    all_bubbles = ResponseSplitter.split_text(clean_text)
    
    # 3. Batching
    current_batch, remaining = ResponseSplitter.get_batch(all_bubbles)
    
    # Determine Keyboard
    keyboard = None
    if remaining:
        # Pagination Mode
        builder = InlineKeyboardBuilder()
        builder.button(text="... Leer más ⬇️", callback_data="smart_page")
        keyboard = builder.as_markup()
        
        # Save State: Remaining bubbles AND final button definition
        await state.update_data(smart_remaining=remaining, smart_final_buttons=button_def)
    else:
        # Done Mode
        keyboard = ResponseSplitter.create_keyboard_from_def(button_def)
        # Clear smart state just in case
        await state.update_data(smart_remaining=[], smart_final_buttons=None)

    # Sending
    # Check if we are replying to a message or handling a callback
    message = message_or_callback if isinstance(message_or_callback, Message) else message_or_callback.message
    
    for i, bubble in enumerate(current_batch):
        is_last = (i == len(current_batch) - 1)
        reply = keyboard if is_last else None
        await message.answer(bubble, reply_markup=reply)

async def continue_smart_response(callback: CallbackQuery, state: FSMContext):
    """
    Called when user clicks "Leer más".
    """
    data = await state.get_data()
    remaining = data.get("smart_remaining", [])
    button_def = data.get("smart_final_buttons", None)
    
    if not remaining:
        await callback.answer("No hay más contenido.")
        return

    # Batching logic again
    current_batch, new_remaining = ResponseSplitter.get_batch(remaining)
    
    keyboard = None
    if new_remaining:
        # Still more -> Next "Leer más"
        builder = InlineKeyboardBuilder()
        builder.button(text="... Leer más ⬇️", callback_data="smart_page")
        keyboard = builder.as_markup()
        await state.update_data(smart_remaining=new_remaining) # Update state
    else:
        # Finished -> Show original intended buttons
        keyboard = ResponseSplitter.create_keyboard_from_def(button_def)
        await state.update_data(smart_remaining=[]) # Clear

    # Send
    # Make sure to acknowledge callback
    await callback.answer()
    
    for i, bubble in enumerate(current_batch):
        is_last = (i == len(current_batch) - 1)
        reply = keyboard if is_last else None
        await callback.message.answer(bubble, reply_markup=reply)
