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
    
    # Try to get last action from the actions table
    action_table_pattern = r'<table[^>]*class="[^"]*table[^"]*"[^>]*>(.*?)</table>'
    action_matches = re.findall(action_table_pattern, html, re.DOTALL)
    
    last_date = ""
    status = ""
    
    if action_matches:
        # Get tables that might contain actions
        for table_html in action_matches:
            # Find all rows
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
            if len(rows) > 1:  # Skip header
                # Get last row
                last_row = rows[-1]
                # Extract cells
                cells = re.findall(r'<td[^>]*>(.*?)</td>', last_row, re.DOTALL)
                if len(cells) >= 1:
                    # Clean up cell content
                    for i, cell in enumerate(cells[:2]):
                        clean_cell = re.sub(r'<[^>]+>', '', cell).strip()
                        if i == 0:
                            last_date = clean_cell
                        elif i == 1:
                            status = clean_cell
    
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
    
    return {
        'Bill Number': bill_data['bill_id'] or bill_id,
        'Title': bill_data['title'],
        'Sponsors': bill_data['sponsors'],
        'Status': bill_data['status'],
        'Current Location/Referral': bill_data['location'],
        'Last Action Date': bill_data['last_date'],
        'URL': url
    }

def main():
    print("NM Legislative Bill Tracker - Complete Version")
    print("=" * 60)
    print("Captures all sponsors and referral information")
    print("Scraping bills from the 2026 session...\n")
    
    bills = []
    session_year = "26"
    
    # Scrape House and Senate bills
    for chamber in ['H', 'S']:
        chamber_name = "House" if chamber == 'H' else "Senate"
        print(f"\n{chamber_name} Bills:")
        print("-" * 60)
        
        bill_num = 1
        consecutive_misses = 0
        
        while bill_num <= 500 and consecutive_misses < 50:
            bill_data = scrape_bill(chamber, bill_num, session_year)
            
            if bill_data:
                bills.append(bill_data)
                # Show first sponsor only in output to keep it clean
                first_sponsor = bill_data['Sponsors'].split(';')[0] if bill_data['Sponsors'] else ""
                print(f"  ✓ {bill_data['Bill Number']}: {bill_data['Title'][:40]}... ({first_sponsor})")
                consecutive_misses = 0
            else:
                consecutive_misses += 1
            
            bill_num += 1
            time.sleep(0.2)  # Be nice to the server
    
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
        print("  • Bill Number")
        print("  • Title")
        print("  • Sponsors (all co-sponsors included, separated by semicolons)")
        print("  • Status (last action)")
        print("  • Current Location/Referral (committee assignment)")
        print("  • Last Action Date")
        print("  • URL (direct link to bill)")
        print("\nYou can open this file in Excel or Google Sheets!")
        print("=" * 60)
    else:
        print("\n❌ No bills found.")

if __name__ == "__main__":
    main()
