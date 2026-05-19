"""
Heatmap Service - Generate heatmap data for market visualization
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class HeatmapService:
    """Generate heatmap data for market visualization"""

    @staticmethod
    def generate_treemap_data(
        symbols_data: List[Dict[str, Any]],
        group_by: str = "sector"
    ) -> Dict[str, Any]:
        """
        Generate treemap data structure for visualization

        Args:
            symbols_data: List of symbol data with change_pct, volume, market_cap
            group_by: Grouping strategy (sector, market_cap_tier, exchange)

        Returns:
            Treemap data structure compatible with D3.js/Recharts
        """
        if group_by == "market_cap_tier":
            return HeatmapService._group_by_market_cap(symbols_data)
        elif group_by == "sector":
            return HeatmapService._group_by_sector(symbols_data)
        else:
            return HeatmapService._flat_structure(symbols_data)

    @staticmethod
    def _group_by_market_cap(symbols_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Group symbols by market cap tiers"""
        large_cap = []
        mid_cap = []
        small_cap = []

        for symbol in symbols_data:
            market_cap = symbol.get("market_cap", 0)

            if market_cap > 1e10:  # > 10B
                large_cap.append(symbol)
            elif market_cap > 1e9:  # > 1B
                mid_cap.append(symbol)
            else:
                small_cap.append(symbol)

        return {
            "name": "Market",
            "children": [
                {
                    "name": "Large Cap",
                    "children": [
                        HeatmapService._format_symbol(s) for s in large_cap
                    ]
                },
                {
                    "name": "Mid Cap",
                    "children": [
                        HeatmapService._format_symbol(s) for s in mid_cap
                    ]
                },
                {
                    "name": "Small Cap",
                    "children": [
                        HeatmapService._format_symbol(s) for s in small_cap
                    ]
                }
            ]
        }

    @staticmethod
    def _group_by_sector(symbols_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Group symbols by sector (simplified categorization)"""
        # Simplified sector mapping
        sectors = {
            "Layer 1": ["BTC", "ETH", "BNB", "ADA", "SOL", "AVAX", "DOT", "ATOM"],
            "DeFi": ["UNI", "AAVE", "LINK", "MKR", "COMP", "SNX", "CRV", "SUSHI"],
            "Layer 2": ["MATIC", "ARB", "OP", "IMX", "LRC"],
            "Meme": ["DOGE", "SHIB", "PEPE", "FLOKI"],
            "Gaming": ["AXS", "SAND", "MANA", "ENJ", "GALA"],
            "Others": []
        }

        grouped = {sector: [] for sector in sectors.keys()}

        for symbol_data in symbols_data:
            symbol = symbol_data.get("symbol", "").replace("USDT", "")
            categorized = False

            for sector, tokens in sectors.items():
                if symbol in tokens:
                    grouped[sector].append(symbol_data)
                    categorized = True
                    break

            if not categorized:
                grouped["Others"].append(symbol_data)

        return {
            "name": "Market",
            "children": [
                {
                    "name": sector,
                    "children": [
                        HeatmapService._format_symbol(s) for s in symbols
                    ]
                }
                for sector, symbols in grouped.items()
                if symbols  # Only include non-empty sectors
            ]
        }

    @staticmethod
    def _flat_structure(symbols_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Flat structure without grouping"""
        return {
            "name": "Market",
            "children": [
                HeatmapService._format_symbol(s) for s in symbols_data
            ]
        }

    @staticmethod
    def _format_symbol(symbol_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format symbol data for treemap"""
        change_pct = symbol_data.get("change_pct", 0)

        # Determine color based on change
        if change_pct > 5:
            color = "#00C853"  # Strong green
        elif change_pct > 0:
            color = "#69F0AE"  # Light green
        elif change_pct > -5:
            color = "#FF5252"  # Light red
        else:
            color = "#D32F2F"  # Strong red

        return {
            "name": symbol_data.get("symbol", ""),
            "value": symbol_data.get("market_cap", 0),
            "change": round(change_pct, 2),
            "price": symbol_data.get("price", 0),
            "volume": symbol_data.get("volume_24h", 0),
            "volatility": symbol_data.get("volatility", 0),
            "color": color
        }

    @staticmethod
    def generate_correlation_heatmap(
        correlation_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate correlation matrix heatmap

        Args:
            correlation_data: List of correlation pairs

        Returns:
            Matrix data for correlation heatmap
        """
        # Extract unique symbols
        symbols = set()
        for item in correlation_data:
            symbols.add(item["symbol_a"])
            symbols.add(item["symbol_b"])

        symbols = sorted(list(symbols))

        # Build correlation matrix
        matrix = []
        correlation_map = {
            (item["symbol_a"], item["symbol_b"]): item["correlation_24h"]
            for item in correlation_data
        }

        for sym_a in symbols:
            row = []
            for sym_b in symbols:
                if sym_a == sym_b:
                    corr = 1.0
                else:
                    corr = correlation_map.get((sym_a, sym_b)) or \
                           correlation_map.get((sym_b, sym_a)) or 0.0
                row.append(round(corr, 3))
            matrix.append(row)

        return {
            "symbols": symbols,
            "matrix": matrix,
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def generate_volume_profile(
        volume_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate volume profile (price levels with volume)

        Args:
            volume_data: Hourly volume distribution

        Returns:
            Volume profile data
        """
        # Group by hour
        hourly_volume = {}
        for item in volume_data:
            hour = item.get("hour", 0)
            volume = item.get("avg_volume", 0)

            if hour not in hourly_volume:
                hourly_volume[hour] = 0
            hourly_volume[hour] += volume

        # Format for chart
        profile = [
            {
                "hour": hour,
                "volume": round(vol, 2),
                "label": f"{hour:02d}:00"
            }
            for hour, vol in sorted(hourly_volume.items())
        ]

        return {
            "profile": profile,
            "peak_hour": max(hourly_volume.items(), key=lambda x: x[1])[0] if hourly_volume else 0,
            "total_volume": sum(hourly_volume.values())
        }
