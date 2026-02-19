#!/usr/bin/env python3
"""
NM Bill Tracker - Complete Version
Captures all sponsors and referral information
"""

import urllib.request
import re
import csv
from datetime import datetime
import time

def fetch_url(url):
    """Fetch a URL"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"    Error fetching: {e}")
        return None

def parse_bill_html(html):
    """Extract bill info using regex patterns"""
    if not html:
        return None
    
    # Check if bill exists
    if 'not found' in html.lower():
        return None
    
    # Extract bill ID
    bill_id_match = re.search(r'id="MainContent_formViewLegislation_lblBillID"[^>]*>([^<]+)</span>', html)
    bill_id = bill_id_match.group(1).strip() if bill_id_match else ""
    
    # Extract title
    title_match = re.search(r'id="MainContent_formViewLegislation_lblTitle"[^>]*>([^<]+)</span>', html)
    title = title_match.group(1).strip() if title_match else ""
    
    # If we don't have at least a title, this probably isn't a valid bill page
    if not title:
        return None
    
    # Extract ALL sponsors (linkSponsor, linkSponsor2, linkSponsor3, etc.)
    sponsors = []
    # First sponsor
    sponsor_match = re.search(r'id="MainContent_formViewLegislation_linkSponsor"[^>]*>([^<]+)</a>', html)
    if sponsor_match:
        sponsors.append(sponsor_match.group(1).strip())
    
    # Additional sponsors (linkSponsor2, linkSponsor3, etc.)
    for i in range(2, 20):  # Check up to 20 co-sponsors
        sponsor_pattern = f'id="MainContent_formViewLegislation_linkSponsor{i}"[^>]*>(?:<br/>)?([^<]+)</a>'
        sponsor_match = re.search(sponsor_pattern, html)
        if sponsor_match:
            sponsors.append(sponsor_match.group(1).strip())
        else:
            break  # Stop when we don't find the next one
    
    # Join all sponsors with semicolons
    all_sponsors = "; ".join(sponsors) if sponsors else ""
    
    # Extract current location/referral
    location_match = re.search(r'id="MainContent_formViewLegislation_linkLocation"[^>]*>([^<]+)</a>', html)
    current_location = location_match.group(1).strip() if location_match else ""
    
    # Extract actions from lblAction spans
    # Format: Legislative Day: X<br/>Calendar Day: MM/DD/YYYY</br><strong>Action text</strong>
    action_pattern = r'dataListActions_lblAction_\d+"[^>]*>(.*?)</span>'
    actions = re.findall(action_pattern, html, re.DOTALL)

    last_date = ""
    status = ""

    if actions:
        # Get the last action (most recent)
        last_action = actions[-1]

        # Extract calendar day
        date_match = re.search(r'Calendar Day:\s*(\d{2}/\d{2}/\d{4})', last_action)
        if date_match:
            last_date = date_match.group(1)

        # Extract action text (inside <strong> tags)
        action_match = re.search(r'<strong>([^<]+)</strong>', last_action)
        if action_match:
            status = action_match.group(1).strip()
    
    return {
        'bill_id': bill_id,
        'title': title,
        'sponsors': all_sponsors,
        'status': status,
        'location': current_location,
        'last_date': last_date
    }

def scrape_bill(chamber, bill_num, session_year="26"):
    """Scrape a single bill"""
    bill_id = f"{chamber}B{bill_num:04d}"
    url = f"https://www.nmlegis.gov/Legislation/Legislation?chamber={chamber}&legType=B&legNo={bill_num}&year={session_year}"
    
    html = fetch_url(url)
    if not html:
        return None
    
    bill_data = parse_bill_html(html)
    if not bill_data:
        return None
    
    # Format bill number as HTML link for Datawrapper
    bill_num_display = bill_data['bill_id'] or bill_id
    bill_link = f'<a href="{url}" target="_blank">{bill_num_display}</a>'

    return {
        'Bill Number': bill_link,
        'Title': bill_data['title'],
        'Sponsors': bill_data['sponsors'],
        'Status': bill_data['status'],
        'Current Location/Referral': bill_data['location'],
        'Last Action Date': bill_data['last_date']
    }

def main():
    print("NM Legislative Bill Tracker - Complete Version")
    print("=" * 60)
    print("Captures all sponsors and referral information")
    print("Scraping bills from the 2026 session...\n")
    
    bills = []
    session_year = "26"
    
    # Scrape House and Senate bills
    # Max bill numbers based on 2026 session (HB goes up to ~380, SB to ~320)
    max_bills = {'H': 400, 'S': 350}

    for chamber in ['H', 'S']:
        chamber_name = "House" if chamber == 'H' else "Senate"
        print(f"\n{chamber_name} Bills:")
        print("-" * 60)

        found_count = 0
        for bill_num in range(1, max_bills[chamber] + 1):
            bill_data = scrape_bill(chamber, bill_num, session_year)

            if bill_data:
                bills.append(bill_data)
                found_count += 1
                # Show first sponsor only in output to keep it clean
                first_sponsor = bill_data['Sponsors'].split(';')[0] if bill_data['Sponsors'] else ""
                print(f"  ✓ {bill_data['Bill Number']}: {bill_data['Title'][:40]}... ({first_sponsor})")

            time.sleep(0.2)  # Be nice to the server

        print(f"  Found {found_count} {chamber_name} bills")
    
    # Save to CSV with consistent filename for GitHub
    if bills:
        filename = 'bills.csv'  # Always same name so Google Sheets URL doesn't change
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=bills[0].keys())
            writer.writeheader()
            writer.writerows(bills)
        
        print("\n" + "=" * 60)
        print(f"✅ SUCCESS! Found {len(bills)} bills")
        print(f"📄 Saved to: {filename}")
        print(f"\nColumns included:")
        print("  • Bill Number (with hyperlink to bill page)")
        print("  • Title")
        print("  • Sponsors (all co-sponsors included, separated by semicolons)")
        print("  • Status (last action)")
        print("  • Current Location/Referral (committee assignment)")
        print("  • Last Action Date")
        print("=" * 60)
    else:
        print("\n❌ No bills found.")

if __name__ == "__main__":
    main()
