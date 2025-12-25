import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Page Configuration
st.set_page_config(
    page_title="Smart Grocery Assistant",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}     
        footer {visibility: hidden;}       
        header {visibility: hidden;}        

        .block-container {
            padding-top: 0.5rem !important;   
        }  
        .app-title {
            font-size: 28px;      
            font-weight: bold;
            color: #2B6CB0;
            margin-top: 0;        
            margin-bottom: 5px;   
        }
        .app-subtitle {
            font-size: 16px;
            color: #4A5568;
            margin-top: 0;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize Session State
if 'grocery_list' not in st.session_state:
    st.session_state.grocery_list = []
if 'purchase_history' not in st.session_state:
    st.session_state.purchase_history = []
if 'settings' not in st.session_state:
    st.session_state.settings = {'auto_suggest': True}

DATA_FILE = 'grocery_data.json'


# Data Persistence
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                st.session_state.grocery_list = data.get('grocery_list', [])
                st.session_state.purchase_history = data.get('purchase_history', [])
                st.session_state.settings.update(data.get('settings', {}))
        except Exception as e:
            st.error(f"Error loading data: {e}")

def save_data():
    try:
        data = {
            'grocery_list': st.session_state.grocery_list,
            'purchase_history': st.session_state.purchase_history,
            'settings': st.session_state.settings
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, default=str, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"Error saving data: {e}")

load_data()

# Healthier Alternatives
HEALTHIER_ALTERNATIVES = {
    'white bread': {'alt': 'whole wheat bread', 'reason': 'Higher fiber, more nutrients, better for digestion'},
    'white rice': {'alt': 'brown rice', 'reason': 'More fiber, vitamins, minerals, and protein'},
    'soda': {'alt': 'sparkling water with lemon', 'reason': 'No added sugar, hydrating, natural flavor'},
    'potato chips': {'alt': 'baked chips', 'reason': 'Lower fat content, more nutrients'},
    'ice cream': {'alt': 'frozen yogurt', 'reason': 'Less fat, fewer calories, probiotics'},
    'butter': {'alt': 'olive oil', 'reason': 'Healthier monounsaturated fats, antioxidants'},
    'whole milk': {'alt': 'skim milk', 'reason': 'Lower fat, fewer calories, plant-based option'},
    'beef': {'alt': 'lean chicken', 'reason': 'Lower saturated fat, more protein, omega-3s'},
    'pasta': {'alt': 'whole wheat pasta', 'reason': 'More fiber, complex carbohydrates, lower calories'},
    'mayonnaise': {'alt': 'Greek yogurt', 'reason': 'More protein, less fat, probiotics'},
    'sugar': {'alt': 'honey', 'reason': 'Natural sweeteners, lower glycemic index'},
    'cookies': {'alt': 'oatmeal cookies', 'reason': 'More fiber, less processed sugar, natural sweetness'},
    'candy': {'alt': 'dark chocolate', 'reason': 'Antioxidants, natural sugars, fiber'},
    'cream': {'alt': 'low-fat milk', 'reason': 'Lower fat content, plant-based option'},
    'bacon': {'alt': 'turkey bacon', 'reason': 'Lower fat, less sodium, more protein'},
    'juice': {'alt': 'fresh fruit', 'reason': 'More fiber, less sugar, natural hydration'},
}

def get_healthier_alt(item_name):
    item_lower = item_name.lower().strip()
    for key, value in HEALTHIER_ALTERNATIVES.items():
        if key in item_lower or item_lower in key:
            return value
    return None

def suggest_healthier_alternatives():
    suggestions = []
    for item in st.session_state.grocery_list:
        alt = get_healthier_alt(item['name'])
        if alt:
            suggestions.append({
                'current': item['name'],
                'alternative': alt['alt'],
                'reason': alt['reason'],
                'item_id': item.get('id')
            })
    return suggestions

# Missing Items Prediction
def predict_missing_items():
    if not st.session_state.settings.get('auto_suggest', True):
        return []

    suggestions = []
    current_items = [item['name'].lower().strip() for item in st.session_state.grocery_list]

    today = datetime.now().date()
    cutoff_days = 20
    cutoff = today - timedelta(days=cutoff_days)

    # Track last purchase date and category
    item_last_date = {}
    item_categories = {}

    for purchase in st.session_state.purchase_history:
        try:
            purchase_date = datetime.strptime(purchase['date'], '%Y-%m-%d').date()
            if purchase_date >= cutoff:
                for item in purchase['items']:
                    name = item['name'].lower().strip()
                    if name not in item_last_date or purchase_date > item_last_date[name]:
                        item_last_date[name] = purchase_date
                        item_categories[name] = item.get('category', 'Other')
        except:
            continue

    # Suggest items not currently in grocery list
    for name, last_date in item_last_date.items():
        if name not in current_items:
            days_since = (today - last_date).days
            suggestions.append({
                'item': name,
                'reason': f"You bought {name} {days_since} day(s) ago. Should I add it again?",
                'category': item_categories.get(name, 'Other')
            })

    return suggestions

# Expiring Items
def get_expiring_items():
    reminders = []
    today = datetime.now().date()

    # Shelf life in days
    shelf_life = {
        'milk': 7, 'bread': 5, 'whole wheat bread': 7, 'eggs': 21, 'yogurt': 14, 'cheese': 30,
        'rice': 180, 'flour': 180, 'pasta': 365, 'sugar': 365, 'honey': 365, 'cookies': 120,
        'chips': 180, 'chocolate': 180, 'mayonnaise': 60, 'meat': 3, 'chicken': 3, 'fish': 2,
        'beef': 3, 'bananas': 5, 'butter': 180, 'bacon': 7, 'juice': 7, 'olive oil': 365,
        'tomatoes': 7, 'onions': 30, 'potatoes': 30, 'apples': 14, 'oranges': 14, 'spinach': 5,
    }

    default_life = 30  # Default shelf life for unknown items

    for item in st.session_state.grocery_list:
        try:
            purchase_date = datetime.strptime(item['added_date'], '%Y-%m-%d').date()
        except:
            continue

        item_name_lower = item['name'].lower().strip()
        item_life = None

        # Try to find shelf life key 
        for key, life in shelf_life.items():
            if key in item_name_lower or item_name_lower in key:
                item_life = life
                break

        if item_life is None:
            item_life = default_life

        days_since_added = (today - purchase_date).days
        days_until_expiry = item_life - days_since_added

        # status logic
        if days_until_expiry < 0:
            status = 'expired'
            message = f"⚠️ {item['name']} expired {abs(days_until_expiry)} day(s) ago!"
        elif days_until_expiry <= 4:
            status = 'urgent'
            message = f"🔴 {item['name']} expires in {days_until_expiry} day(s)!"
        elif days_until_expiry <= 6:
            status = 'warning'
            message = f"🟡 {item['name']} expires in {days_until_expiry} day(s)"
        else:
            status = 'fresh'
            message = None  # No alert for fresh items

        # Only show alerts up to 8 days
        if status != 'fresh' and days_until_expiry <= 8:
            reminders.append({
                'item': item['name'],
                'status': status,
                'message': message
            })

    status_order = {'expired': 0, 'urgent': 1, 'warning': 2, 'fresh': 3}
    reminders_sorted = sorted(reminders, key=lambda x: status_order.get(x['status'], 4))

    return reminders_sorted

# Purchase History DF
def get_purchase_history_df():
    rows = []
    for purchase in st.session_state.purchase_history:
        for item in purchase['items']:
            rows.append({
                "Item Name": item['name'],
                "Category": item['category'],
                "Quantity": item['quantity'],
                "Purchase Date": purchase['date'],
                "Expired Date": item.get('expired_date', "")
            })
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame()

st.markdown("""
<style>
.card {
    padding: 18px;
    border-radius: 14px;
    background-color: #ffffff;
    box-shadow: 0 6px 18px rgba(0,0,0,0.06);
    margin-bottom: 18px;
}
.grocery-row {
    padding: 10px;
    border-radius: 10px;
    background-color: #fbfcfd;
    border: 1px solid #eef1f5;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
}
.grocery-name {
    font-weight: 600;
    font-size: 15px;
}
.grocery-meta {
    color: #666;
    font-size: 13px;
}
.small-btn {
    padding: 6px 12px;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# Main App
def main():
  
    # App Title
    st.markdown('<div class="app-title">Smart Grocery Shopping Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">AI-powered assistant that predicts missing items, suggests healthier alternatives, and reminds you about expiring products</div>', unsafe_allow_html=True)

    # Add Item & Grocery List
    row1_col1, row1_col2 = st.columns([1, 2])

    # Add Item
    with row1_col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h3 style="color:#38A169;">Add Item</h3>', unsafe_allow_html=True)
        with st.form("add_item", clear_on_submit=True):
            item_name = st.text_input("Item Name", placeholder="e.g., Milk, Bread, Eggs")
            category = st.selectbox(
                "Category",
                ["Dairy", "Fruits", "Vegetables", "Meat", "Bakery", "Beverages", "Snacks", "Grains", "Condiments", "Other"]
            )
            quantity = st.number_input("Quantity", min_value=1, value=1, step=1, format="%d")
            submit = st.form_submit_button("Add to List", key="add_item")
        if submit:
            if item_name.strip():
                new_item = {
                    'id': len(st.session_state.grocery_list) + 1,
                    'name': item_name.strip(),
                    'category': category,
                    'quantity': quantity,
                    'added_date': datetime.now().strftime('%Y-%m-%d'),
                    'purchased': False
                }
                st.session_state.grocery_list.insert(0, new_item)  
                save_data()
                st.success(f" Added {item_name}!")
            else:
                st.error("Please enter an item name!")
        st.markdown('</div>', unsafe_allow_html=True)

    # Grocery List
    with row1_col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h3 style="color:#DD6B20;"> Current Grocery List</h3>', unsafe_allow_html=True)
        if st.session_state.grocery_list:
            col_labels = st.columns([0.5, 4, 1, 1, 1])
            col_labels[0].markdown("****")
            col_labels[1].markdown("**Item**")
            col_labels[2].markdown("**Qty**")
            col_labels[3].markdown("**Add**")
            col_labels[4].markdown("**Remove**")

            for idx, item in enumerate(st.session_state.grocery_list):
                unique_key = f"{idx}_{item.get('id', idx)}"
                col1, col2, col3, col4, col5 = st.columns([0.5, 4, 1, 1, 1])
                with col1:
                    purchased = st.checkbox("", value=item.get('purchased', False), key=f"cb_{unique_key}", label_visibility="collapsed")
                    if purchased != item.get('purchased', False):
                        st.session_state.grocery_list[idx]['purchased'] = purchased
                        save_data()
                        st.rerun()
                with col2:
                    quantity_display = str(int(item['quantity']))
                    st.markdown(f"<div class='grocery-row'><div style='flex:1'><div class='grocery-name'>{item['name']}</div><div class='grocery-meta'>{item['category']}</div></div></div>", unsafe_allow_html=True)
                    alt = get_healthier_alt(item['name'])
                    if alt:
                        st.markdown(f"<p style='color:#38A169;'>Healthier option: {alt['alt']} — {alt['reason']}</p>", unsafe_allow_html=True)
                with col3:
                    st.write(quantity_display)
                with col4:
                    if st.button("Add", key=f"purchase_{unique_key}", use_container_width=True):
                        checked_items = [i for i in st.session_state.grocery_list if i.get('purchased', False)]
                        to_purchase = checked_items if checked_items else [item]
                        if to_purchase:
                            purchase_record = {
                                'date': datetime.now().strftime('%Y-%m-%d'),
                                'items': [
                                    {
                                        'name': i['name'],
                                        'category': i['category'],
                                        'quantity': i['quantity'],
                                        'added_date': i.get('added_date', datetime.now().strftime('%Y-%m-%d')),
                                        'expired_date': None
                                    } for i in to_purchase
                                ]
                            }
                            # calculate expiry dates
                            shelf_life = {
                                'milk': 7, 'bread': 5, 'whole wheat bread': 7, 'eggs': 21, 'yogurt': 14, 'cheese': 30,
                                'rice': 180, 'flour': 180, 'pasta': 365, 'sugar': 365, 'honey': 365, 'cookies': 120,
                                'chips': 180, 'chocolate': 180, 'mayonnaise': 60, 'meat': 3, 'chicken': 3, 'fish': 2,
                                'beef': 3, 'bananas': 5, 'butter': 180, 'bacon': 7, 'juice': 7, 'olive oil': 365,
                                'tomatoes': 7, 'onions': 30, 'potatoes': 30, 'apples': 14, 'oranges': 14, 'spinach': 5,
                            }
                            for item_p in purchase_record['items']:
                                item_name_lower = item_p['name'].lower()
                                item_life = None
                                for key, life in shelf_life.items():
                                    if key in item_name_lower:
                                        item_life = life
                                        break
                                if item_life:
                                    item_p['expired_date'] = (datetime.now() + timedelta(days=item_life)).strftime('%Y-%m-%d')
                                else:
                                    item_p['expired_date'] = ""
                            st.session_state.purchase_history.insert(0, purchase_record) 
                            to_purchase_names = set([i['name'] for i in to_purchase])
                            st.session_state.grocery_list = [i for i in st.session_state.grocery_list if i['name'] not in to_purchase_names]
                            save_data()
                            st.success(f"Purchased {len(purchase_record['items'])} item(s)!")
                            st.rerun()
                with col5:
                    if st.button("Remove", key=f"del_{unique_key}", use_container_width=True):

                        try:
                            st.session_state.grocery_list.pop(idx)
                            save_data()
                            st.success(f"Removed {item['name']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not remove item: {e}")
        else:
            st.info("Your grocery list is empty. Add items above!")
        st.markdown('</div>', unsafe_allow_html=True)

    # Suggestions / Expiring
    row2_col1, row2_col2, row2_col3 = st.columns([1,1,1])

    # Healthier Alternatives
    with row2_col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color:#38A169;">Healthier Alternatives</h4>', unsafe_allow_html=True)
        healthier_suggestions = suggest_healthier_alternatives()
        if healthier_suggestions:
            for sug_idx, sug in enumerate(healthier_suggestions):
                with st.expander(f"Replace '{sug['current']}' with '{sug['alternative']}'"):
                    st.markdown(f"<p style='color:#3182CE;'>Reason: {sug['reason']}</p>", unsafe_allow_html=True)
                    if st.button("Replace", key=f"rep_{sug_idx}_{sug['item_id']}", use_container_width=True):
                        for item in st.session_state.grocery_list:
                            if item.get('id') == sug['item_id']:
                                item['name'] = sug['alternative']
                                save_data()
                                st.success(f"Replaced with {sug['alternative']}!")
                                st.rerun()
        else:
            st.info("No unhealthy items detected.")
        st.markdown('</div>', unsafe_allow_html=True)

    # AI Missing Items
    with row2_col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color:#3182CE;">AI Missing Items</h4>', unsafe_allow_html=True)
        
        # Only predict missing items if grocery list is not empty
        if st.session_state.grocery_list:
            missing_items = predict_missing_items()
            # Filter out items already in the grocery list
            current_items = [item['name'].lower().strip() for item in st.session_state.grocery_list]
            missing_items = [item for item in missing_items if item['item'].lower().strip() not in current_items]
            
            if missing_items:
                for sug_idx, sug in enumerate(missing_items):
                    with st.expander(f"{sug['item']}"):
                        st.markdown(f"<p style='color:#4A5568;'>Reason: {sug['reason']}</p>", unsafe_allow_html=True)
                        if st.button("Add", key=f"add_missing_{sug_idx}", use_container_width=True):
                            new_item = {
                                'id': len(st.session_state.grocery_list) + 1,
                                'name': sug['item'],
                                'category': sug.get('category', 'Other'),
                                'quantity': 1.0,
                                'added_date': datetime.now().strftime('%Y-%m-%d'),
                                'purchased': False
                            }
                            st.session_state.grocery_list.append(new_item)
                            save_data()
                            st.success(f"Added {sug['item']} to your list!")
                            st.rerun()
            else:
                st.info("No missing item suggestions now.")
        else:
            st.info("Your grocery list is empty. Add items to see AI suggestions.")
        
        st.markdown('</div>', unsafe_allow_html=True)


    # Expiring Items
    with row2_col3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color:#DD6B20;">Expiring Items</h4>', unsafe_allow_html=True)
        exp_items = get_expiring_items()
        if exp_items:
            for item_m in exp_items:
                st.markdown(f"<p style='color:#E53E3E;'>{item_m['message'] if isinstance(item_m, dict) else item_m}</p>", unsafe_allow_html=True)
        else:
            st.info(" No items expiring soon.")
        st.markdown('</div>', unsafe_allow_html=True)

    
    # Purchase History
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3 style="color:#718096;"> Purchase History</h3>', unsafe_allow_html=True)
    ph_df = get_purchase_history_df()
    if not ph_df.empty:
        st.dataframe(ph_df.sort_values(by="Purchase Date", ascending=False))
    else:
        st.info(" No purchase history yet.")
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
