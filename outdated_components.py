import asyncio
import json
import os
from playwright.async_api import async_playwright

def read_credentials(file_path):
    credentials = []
    try:
        with open(file_path, 'r') as file:
            content = file.read().strip().split('\n\n')  # Split by double newline to separate accounts
            for block in content:
                lines = block.split('\n')
                if len(lines) >= 2:
                    email = lines[0].strip()
                    password = lines[1].strip()
                    credentials.append((email, password))
    except Exception as e:
        print(f"Error reading credentials file: {e}")
    return credentials

def read_domains(file_path):
    domains = []
    try:
        with open(file_path, 'r') as file:
            domains = [line.strip() for line in file.readlines() if line.strip()]
    except Exception as e:
        print(f"Error reading domains file: {e}")
    return domains

async def fetch_technology_stack(page, domain):
    try:
        # Focus on the input field and type the domain
        await page.click('#input-80')
        await page.type('#input-80', (" " + domain), delay=350)
        
        # Wait for the suggestion to appear
        suggestion_selector = f'text="{domain}"'
        try:
            await page.wait_for_selector(suggestion_selector, timeout=15000)
            # Click the correct suggestion
            await page.click(suggestion_selector)
            # Wait for the technology stack to load
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(5)  # Adding a delay to ensure all dynamic content is loaded

            # Extract technology stack information
            tech_stack_selector = '.technology-list'  # Adjust this to match the actual selector
            await page.wait_for_selector(tech_stack_selector, timeout=20000)  # Ensure the technology list is loaded

            tech_stack_element = await page.query_selector(tech_stack_selector)

            if tech_stack_element:
                tech_stack_text = await tech_stack_element.inner_text()
                return tech_stack_text.strip().split('\n')  # Splitting into list if required
            else:
                print(f"Technology stack not found for {domain}")
                return ["No technology stack found"]

        except Exception as e:
            print(f"No suggestions available for {domain}, skipping. Error: {e}")
            with open("domains_without_suggestions.txt", "a", encoding="utf-8") as file:
                file.write(f"{domain}\n")
            return ["No suggestions available"]

    except Exception as e:
        print(f"Error fetching technology stack for {domain}: {e}")
        return ["Error occurred"]

async def analyze_websites(page, websites, results_file):
    try:
        # Wait for the URL input field to be available
        await page.wait_for_selector('#input-80', timeout=60000)

        # Loop through each website
        for website in websites:
            try:
                print(f"Analyzing website: {website}")

                # Click on the input field to focus
                await page.click('#input-80')

                # Type the website URL slowly to allow suggestion box to appear
                await page.type('#input-80', (" " + website), delay=350)  # Increased delay to simulate slower typing

                # Wait for the suggestion box to appear
                suggestion_selector = f'text="{website}"'
                try:
                    await page.wait_for_selector(suggestion_selector, timeout=10000)
                    # Click the correct suggestion
                    await page.click(suggestion_selector)
                    print(f"Suggestion found and clicked for: {website}")

                    # Submit the search (if needed; often clicking the suggestion is enough)
                    await page.press('#input-80', 'Enter')

                    # Wait for the results to load
                    await page.wait_for_load_state('networkidle')

                    # Retrieve all visible text from specific parts of the page
                    result_element = await page.query_selector('main')  # Adjust selector as needed
                    if result_element:
                        page_text = await result_element.inner_text()
                    else:
                        page_text = "No data found."

                    # Prepare result for JSON
                    result = {
                        "domain": website,
                        "technology_stack": page_text.strip().split('\n')  # Splitting into list if required
                    }

                    # Add the result to the JSON output and write immediately
                    with open(results_file, "r+", encoding="utf-8") as file:
                        data = json.load(file)
                        data.append(result)
                        file.seek(0)
                        json.dump(data, file, indent=4)

                except Exception as e:
                    print(f"No suggestions available for {website}, skipping. Error: {e}")
                    result = {
                        "domain": website,
                        "technology_stack": ["No suggestions available"]
                    }

                    # Add the result to the JSON output and write immediately
                    with open(results_file, "r+", encoding="utf-8") as file:
                        data = json.load(file)
                        data.append(result)
                        file.seek(0)
                        json.dump(data, file, indent=4)

                # Go back to the home page to reset the search
                await page.goto("https://www.wappalyzer.com/")
                await page.wait_for_load_state('networkidle')  # Wait for the home page to fully load

            except Exception as e:
                print(f"Error processing {website}: {e}")
                result = {
                    "domain": website,
                    "technology_stack": [f"Error: {e}"]
                }

                # Add the result to the JSON output and write immediately
                with open(results_file, "r+", encoding="utf-8") as file:
                    data = json.load(file)
                    data.append(result)
                    file.seek(0)
                    json.dump(data, file, indent=4)

            # Optional sleep to avoid overloading the server
            await asyncio.sleep(2)

    except Exception as e:
        print(f"Error during website analysis: {e}")
        return

async def logout(page):
    try:
        # Add logout functionality based on the website's structure
        print("Logging out...")
        await page.click('text="Logout"')  # Example selector for the logout button
        await page.wait_for_load_state('networkidle')
        print("Logout successful.")
    except Exception as e:
        print(f"Error during logout: {e}")

async def main():
    # Load credentials
    credentials_list = read_credentials('credentials.txt')
    if not credentials_list:
        print("Failed to load credentials. Please check the credentials file.")
        return

    # Load domains
    websites = read_domains('domains.txt')
    if not websites:
        print("No websites to analyze. Please check the domains file.")
        return

    # Check if output files exist, if not create them
    if not os.path.exists("website_analysis_results.json"):
        print("Creating website_analysis_results.json")
        with open("website_analysis_results.json", "w", encoding="utf-8") as json_file:
            json.dump([], json_file)  # Create an empty JSON file

    if not os.path.exists("domains_without_suggestions.txt"):
        print("Creating domains_without_suggestions.txt")
        with open("domains_without_suggestions.txt", "w", encoding="utf-8") as file:
            pass  # Create an empty file

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Non-headless mode for debugging
        for EMAIL, PASSWORD in credentials_list:
            print(f"Logging in with account: {EMAIL}")
            try:
                context = await browser.new_context()
                page = await context.new_page()

                # Go to Wappalyzer main page
                await page.goto("https://www.wappalyzer.com/")
                await page.wait_for_load_state('networkidle')  # Wait for the network to be idle

                # Click the "Sign in" button
                try:
                    await page.click('span.v-btn__content >> text="Sign in"')
                    await page.wait_for_load_state('networkidle')  # Wait for the network to be idle
                except Exception as e:
                    print(f"Error clicking 'Sign in' button for {EMAIL}: {e}")
                    await browser.close()
                    continue  # Move to the next set of credentials

                # Wait for the email input field to be available
                try:
                    await page.wait_for_selector('#input-355', timeout=120000)  # Increased timeout to 120 seconds
                except Exception as e:
                    print(f"Error waiting for email input field for {EMAIL}: {e}")
                    await browser.close()
                    continue  # Move to the next set of credentials

                # Fill in the login form
                await page.fill('#input-355', EMAIL)  # Email field
                await page.fill('#input-356', PASSWORD)  # Password field
                await page.click('button[type="submit"]')

                # Check if login was successful by verifying a user-specific element or page change
                try:
                    # Instead of checking for a specific element, wait for a certain time and assume login success
                    await asyncio.sleep(5)
                    print(f"Proceeding with domain analysis for {EMAIL}")
                except Exception as e:
                    print(f"Login likely failed for {EMAIL}, but proceeding with domain analysis anyway: {e}")

                # Analyze websites using the current account
                await analyze_websites(page, websites, "website_analysis_results.json")

                # Logout after processing all domains
                await logout(page)

            except Exception as e:
                print(f"Unexpected error for account {EMAIL}: {e}")

            finally:
                # Ensure context is closed properly
                await context.close()

        await browser.close()

# Run the main function
asyncio.run(main())
