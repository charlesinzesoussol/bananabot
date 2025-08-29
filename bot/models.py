"""Data models for BananaBot user history and batch processing."""

import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from pathlib import Path

# Data storage path - mounted volume for persistence on VPS, local fallback for dev
DATA_ROOT = None

def get_data_root():
    """Get data root path with VPS volume fallback."""
    # Try different possible volume mount paths
    possible_vps_paths = [
        Path("/mnt/HC_Volume_103242903/bananabot-data"),  # Volume ID format
        Path("/mnt/volume-ash-2/bananabot-data"),        # Name format  
        Path("/volume1/bananabot-data"),                 # Alternative mount
        Path("/opt/bananabot-data")                      # Alternative location
    ]
    local_path = Path("data")
    
    # Check each possible VPS path
    for vps_path in possible_vps_paths:
        try:
            if vps_path.parent.exists() and os.access(vps_path.parent, os.W_OK):
                return vps_path
        except:
            continue
    
    return local_path

def ensure_data_directories():
    """Ensure all data directories exist."""
    global DATA_ROOT
    if DATA_ROOT is None:
        DATA_ROOT = get_data_root()
    
    try:
        (DATA_ROOT / "user_galleries").mkdir(parents=True, exist_ok=True)
        (DATA_ROOT / "user_stats").mkdir(parents=True, exist_ok=True)
        (DATA_ROOT / "batch_requests").mkdir(parents=True, exist_ok=True)
        print(f"Data directories ensured at: {DATA_ROOT}")
    except Exception as e:
        print(f"Warning: Could not create data directories at {DATA_ROOT}: {e}")
        # Fallback to local directories
        DATA_ROOT = Path("data")
        (DATA_ROOT / "user_galleries").mkdir(parents=True, exist_ok=True)
        (DATA_ROOT / "user_stats").mkdir(parents=True, exist_ok=True)
        (DATA_ROOT / "batch_requests").mkdir(parents=True, exist_ok=True)
        print(f"Using fallback data path: {DATA_ROOT}")

def get_data_path():
    """Get current data root path."""
    global DATA_ROOT
    if DATA_ROOT is None:
        DATA_ROOT = get_data_root()
    return DATA_ROOT

class ImageWork(BaseModel):
    """Represents a user's image generation work."""
    
    id: str = Field(..., description="Unique ID for this work")
    user_id: str = Field(..., description="Discord user ID")
    prompt: str = Field(..., description="Original prompt used")
    image_url: str = Field(..., description="URL or path to generated image")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    modified_at: datetime = Field(default_factory=datetime.utcnow)
    generation_type: str = Field(default="create", description="create, edit, batch")
    parent_id: Optional[str] = Field(None, description="ID of original work if this is a modification")
    batch_id: Optional[str] = Field(None, description="Batch ID if generated in bulk")
    cost: float = Field(default=0.039, description="API cost for this generation")
    
class UserGallery(BaseModel):
    """User's image gallery and history."""
    
    user_id: str
    works: List[ImageWork] = Field(default_factory=list)
    total_generations: int = Field(default=0)
    total_cost: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_work(self, work: ImageWork) -> None:
        """Add new work to gallery."""
        self.works.append(work)
        self.total_generations += 1
        self.total_cost += work.cost
        self.updated_at = datetime.utcnow()
        self.save()
    
    def get_recent_works(self, limit: int = 10) -> List[ImageWork]:
        """Get recent works."""
        return sorted(self.works, key=lambda x: x.created_at, reverse=True)[:limit]
    
    def get_work_by_id(self, work_id: str) -> Optional[ImageWork]:
        """Get specific work by ID."""
        return next((w for w in self.works if w.id == work_id), None)
    
    def save(self) -> None:
        """Save gallery to file on mounted volume."""
        ensure_data_directories()
        
        file_path = get_data_path() / "user_galleries" / f"{self.user_id}.json"
        with open(file_path, 'w') as f:
            json.dump(self.model_dump(), f, default=str, indent=2)
    
    @classmethod
    def load(cls, user_id: str) -> 'UserGallery':
        """Load gallery from file on mounted volume."""
        ensure_data_directories()
        file_path = get_data_path() / "user_galleries" / f"{user_id}.json"
        
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
                return cls(**data)
        else:
            return cls(user_id=user_id)

class BatchRequest(BaseModel):
    """Batch processing request."""
    
    batch_id: str = Field(..., description="Unique batch ID")
    user_id: str = Field(..., description="Discord user ID")
    prompts: List[str] = Field(..., description="List of prompts to process")
    status: str = Field(default="pending", description="pending, processing, completed, failed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    results: List[Dict[str, Any]] = Field(default_factory=list)
    cost_savings: float = Field(default=0.0)
    
    def save(self) -> None:
        """Save batch request to file on mounted volume."""
        ensure_data_directories()
        
        file_path = get_data_path() / "batch_requests" / f"{self.batch_id}.json"
        with open(file_path, 'w') as f:
            json.dump(self.model_dump(), f, default=str, indent=2)
    
    @classmethod
    def load(cls, batch_id: str) -> Optional['BatchRequest']:
        """Load batch request from file on mounted volume."""
        ensure_data_directories()
        file_path = get_data_path() / "batch_requests" / f"{batch_id}.json"
        
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
                return cls(**data)
        return None

class UserStats(BaseModel):
    """User statistics and usage tracking."""
    
    user_id: str
    total_generations: int = 0
    total_edits: int = 0
    total_batches: int = 0
    total_cost: float = 0.0
    total_savings: float = 0.0
    favorite_prompts: List[str] = Field(default_factory=list)
    most_used_styles: Dict[str, int] = Field(default_factory=dict)
    first_generation: Optional[datetime] = None
    last_generation: Optional[datetime] = None
    
    def update_stats(self, work: ImageWork) -> None:
        """Update stats with new work."""
        if work.generation_type == "create":
            self.total_generations += 1
        elif work.generation_type == "edit":
            self.total_edits += 1
        elif work.generation_type == "batch":
            self.total_batches += 1
            
        self.total_cost += work.cost
        
        if self.first_generation is None:
            self.first_generation = work.created_at
        self.last_generation = work.created_at
        
        # Track favorite prompts (simplified)
        if work.prompt not in self.favorite_prompts:
            self.favorite_prompts.append(work.prompt)
        
        self.save()
    
    def save(self) -> None:
        """Save stats to file on mounted volume."""
        ensure_data_directories()
        
        file_path = get_data_path() / "user_stats" / f"{self.user_id}.json"
        with open(file_path, 'w') as f:
            json.dump(self.model_dump(), f, default=str, indent=2)
    
    @classmethod
    def load(cls, user_id: str) -> 'UserStats':
        """Load stats from file on mounted volume."""
        ensure_data_directories()
        file_path = get_data_path() / "user_stats" / f"{user_id}.json"
        
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
                return cls(**data)
        else:
            return cls(user_id=user_id)