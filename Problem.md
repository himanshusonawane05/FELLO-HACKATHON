Fello AI Builder Hackathon
You have 48 hours to design and build an AI system based on the challenge below.
The goal is not perfection, we want to see how you think, design systems, and build with AI.
You may use any tools, models, frameworks, APIs, or datasets.
You may simulate inputs or use public data if needed.
Focus on building a working end-to-end prototype.

Project
AI Account Intelligence & Enrichment System
Problem
Sales and marketing teams deal with two major data problems:
Anonymous website visitors provide little actionable insight.


Incomplete company data makes it hard to prioritize accounts.


Analytics tools show traffic, but not who the visitor is, what company they represent, or how sales should act.
The challenge is to build an AI system that converts raw signals or minimal company inputs into structured account intelligence and sales actions.
Your system should be able to take either visitor activity or company names and automatically discover, enrich, and analyze company information.

Example Inputs
Your system may accept either of the following.
Website Visitor Signals
Visitor activity data such as:
Visitor ID: 001
 IP: 34.201.xxx.xxx
Pages visited:
/pricing


/ai-sales-agent


/case-studies


Time on site: 3m 42s
 Visits this week: 3
Additional signals may include:
Referral source


Device / location metadata


Visit timestamps


You may simulate visitor traffic or create your own dataset.

Company List
Your system may also accept minimal company inputs, such as:
BrightPath Lending
 Summit Realty Group
 Rocket Mortgage
 Redfin
 Compass Real Estate
Optional inputs may include:
Company Name + Partial Domain

What Your System Should Do
Your AI system should convert raw signals into sales-ready company intelligence.

1. Company Identification
Determine the likely company behind the visitor or input.
Possible approaches:
Reverse IP lookup


Public enrichment APIs


Web scraping


AI research agents


Example Output
Company: Acme Mortgage
 Domain: acmemortgage.com
 Industry: Mortgage Lending
 Company Size: 200 employees
 Location: Texas, USA

2. Persona Inference
Infer the likely role or persona of the visitor based on behavior.
Examples:
Pricing page → buyer intent
 Documentation → technical persona
 Blog content → research stage
Example:
Likely Persona: Head of Sales Operations
 Confidence: 72%

3. Intent Scoring
Estimate the likelihood that the visitor is in an active buying journey.
Signals may include:
Pricing page visits
 Repeat visits
 High dwell time
 Product page activity
Example:
Intent Score: 8.4 / 10
 Stage: Evaluation

4. Company Profile Enrichment
Automatically discover and structure company information such as:
Website


Industry


Company size


Headquarters


Founding year


Business description


Example
Company: BrightPath Lending
Website: brightpathlending.com
Industry: Mortgage Lending
Headquarters: Chicago, USA

Technology Stack Detection
Attempt to identify technologies used by the company.
Examples:
CRM: Salesforce
Marketing Automation: HubSpot
Website Platform: WordPress
Analytics: Google Analytics

Business Signals
Identify indicators of growth or opportunity.
Examples:
Hiring activity
Funding announcements
Market expansion
Product launches

Leadership Discovery
Identify potential decision makers such as:
CEO / Founder
VP Sales
 Head of Marketing
 RevOps leaders

AI Account Intelligence Summary
Generate a concise AI research summary about the company.
Example
Acme Mortgage is a mid-sized lender operating in Texas.
 Recent browsing behavior indicates evaluation of AI sales automation tools.
 Multiple visits to pricing and case studies suggest strong purchase intent.

Recommended Sales Action
Suggest what the sales team should do next.
Example
High-intent visitor detected from Acme Mortgage.
Suggested actions:
Research VP Sales or RevOps leaders


Add account to outbound campaign


Send personalized outreach referencing mortgage case studies



Expected Output
Your system should produce structured intelligence such as:
Company Name
 Website / Domain
 Industry
 Company Size
 Headquarters
 Likely Persona
 Intent Score
 Intent Stage
 AI Summary
 Recommended Sales Action
Additional enrichment may include:
Technology Stack
 Leadership
 Key Signals Observed
 Business Signals

Optional Extensions
You may extend the system with:
multi-agent research workflows


automated enrichment pipelines


CRM integrations


real-time visitor monitoring


historical visitor tracking


vector databases or RAG


data confidence scoring


batch processing



What We Are Evaluating
We care more about how you build the system than perfect accuracy.
We will evaluate:
System design and architecture


Use of AI agents and LLM workflows


Handling messy real-world data


Structured outputs and reasoning


Creativity and builder mindset


Ability to ship a working end-to-end prototype quickly



Submission Requirements
Please submit the following:
1. GitHub Repository
 Public repo with your code and a README explaining setup and system design.
2. Loom Demo Video
 5–10 minute demo explaining the problem, your approach, and showing the system working.
3. Deployed Link (Bonus)
 Live link to the prototype or instructions to run locally.
4. Short Presentation (optional)
 A brief 2 slide deck covering the project, architecture, key features, and example outputs.



Build something interesting. Ship fast. Be creative.

