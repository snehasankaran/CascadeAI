"""Function calling tool definitions for Gemma 4 agents.

Each schema follows the OpenAI tools format so it works with both
Google AI Studio and Ollama endpoints.
"""

EVENT_DETECTOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_acled_events",
            "description": "Search ACLED for recent conflict events in a region",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {"type": "string", "description": "Region or country name"},
                    "days": {"type": "integer", "description": "Look back N days", "default": 30},
                },
                "required": ["region"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_gdelt_events",
            "description": "Search GDELT for global events matching a theme",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Event keyword or theme"},
                    "days": {"type": "integer", "description": "Look back N days", "default": 30},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_historical_severity",
            "description": "Retrieve historical severity scores for similar past events",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_type": {"type": "string", "description": "Type of crisis event"},
                    "region": {"type": "string", "description": "Affected region"},
                },
                "required": ["event_type"],
            },
        },
    },
]

IMPACT_PREDICTOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_food_prices",
            "description": "Fetch food commodity prices for a country",
            "parameters": {
                "type": "object",
                "properties": {
                    "country": {"type": "string", "description": "Country name or ISO3 code"},
                    "commodity": {"type": "string", "description": "e.g. wheat, maize, rice"},
                    "months": {"type": "integer", "description": "Historical months to retrieve", "default": 12},
                },
                "required": ["country", "commodity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_health_indicators",
            "description": "Fetch WHO health indicators for a country",
            "parameters": {
                "type": "object",
                "properties": {
                    "country": {"type": "string", "description": "Country name or ISO3 code"},
                    "indicator": {"type": "string", "description": "e.g. malnutrition, cholera, under5_mortality"},
                },
                "required": ["country", "indicator"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_displacement_data",
            "description": "Fetch UNHCR displacement data for a country",
            "parameters": {
                "type": "object",
                "properties": {
                    "country": {"type": "string", "description": "Country name or ISO3 code"},
                    "months": {"type": "integer", "description": "Historical months", "default": 12},
                },
                "required": ["country"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_energy_prices",
            "description": "Fetch energy commodity prices",
            "parameters": {
                "type": "object",
                "properties": {
                    "commodity": {"type": "string", "description": "e.g. brent_crude, natural_gas, diesel, urea"},
                    "months": {"type": "integer", "description": "Historical months", "default": 12},
                },
                "required": ["commodity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_country_profile",
            "description": "Load the full country vulnerability profile",
            "parameters": {
                "type": "object",
                "properties": {
                    "country": {"type": "string", "description": "Country name"},
                },
                "required": ["country"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cascade_path",
            "description": "Retrieve the BFS cascade path between two nodes",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_node": {"type": "string", "description": "Source node ID"},
                    "to_node": {"type": "string", "description": "Target node ID"},
                },
                "required": ["from_node", "to_node"],
            },
        },
    },
]

DISPATCHER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_reliefweb_plans",
            "description": "Search ReliefWeb for existing response plans",
            "parameters": {
                "type": "object",
                "properties": {
                    "country": {"type": "string", "description": "Country name"},
                    "crisis_type": {"type": "string", "description": "e.g. food_crisis, conflict, flood"},
                },
                "required": ["country"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_response_templates",
            "description": "Get response plan templates for a stakeholder type",
            "parameters": {
                "type": "object",
                "properties": {
                    "stakeholder": {"type": "string", "description": "e.g. WFP, WHO, UNHCR, government"},
                },
                "required": ["stakeholder"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_logistics_data",
            "description": "Get logistics and supply chain data for a region",
            "parameters": {
                "type": "object",
                "properties": {
                    "country": {"type": "string", "description": "Country name"},
                    "supply_type": {"type": "string", "description": "e.g. food_aid, medical, shelter"},
                },
                "required": ["country"],
            },
        },
    },
]
