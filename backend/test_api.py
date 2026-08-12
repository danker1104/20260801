import httpx
import asyncio
import json

async def test_api():
    async with httpx.AsyncClient() as client:
        # Test 1: Get restaurants
        response = await client.get(
            "http://localhost:8000/api/restaurants/nearby",
            params={"lat": 35.1650, "lng": 129.1700, "radius": 1000}
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Total restaurants: {data['total']}")
        print(f"Returned: {len(data['restaurants'])} restaurants")
        
        if data['restaurants']:
            first = data['restaurants'][0]
            print(f"\nFirst restaurant:")
            print(f"  Name: {first['name']}")
            print(f"  Category: {first['category']}")
            print(f"  Distance: {first['distance']:.2f}m")
            print(f"  Rating: {first['externalRating']}")
            print(f"  Recommend Score: {first.get('recommendScore', 'N/A')}")
        
        # Test 2: Sort by distance
        print("\n\nTesting sort by distance...")
        response = await client.get(
            "http://localhost:8000/api/restaurants/nearby",
            params={"lat": 35.1650, "lng": 129.1700, "radius": 1000, "sortBy": "distance"}
        )
        data = response.json()
        print(f"Distance sort - Total: {data['total']}")
        if data['restaurants']:
            for i, r in enumerate(data['restaurants'][:3]):
                print(f"  {i+1}. {r['name']} - {r['distance']:.2f}m")

asyncio.run(test_api())
