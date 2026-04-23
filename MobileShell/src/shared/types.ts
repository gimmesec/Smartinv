export type Tokens = {
  access: string;
  refresh: string;
};

export type UserProfile = {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
  is_superuser: boolean;
  is_admin: boolean;
};

export type Asset = {
  id: number;
  name: string;
  inventory_number: string;
  status: string;
  legal_entity: number;
};

export type InventorySession = {
  id: number;
  status: string;
  legal_entity: number;
  location: number | null;
};

export type InventoryItemResponse = {
  id: number;
  session: number;
  asset: number;
  condition: string;
  comment: string;
};
