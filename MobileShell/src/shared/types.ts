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
  employee_id: number | null;
  employee_name: string;
  legal_entity_id: number | null;
  legal_entity_name: string;
};

export type LegalEntity = {
  id: number;
  name: string;
  tax_id: string;
};

export type Location = {
  id: number;
  legal_entity: number;
  name: string;
  type: string;
  parent: number | null;
};

export type Employee = {
  id: number;
  full_name: string;
  legal_entity: number;
};

export type Asset = {
  id: number;
  name: string;
  inventory_number: string;
  status: string;
  legal_entity: number;
  location: number | null;
  responsible_employee: number | null;
  description: string;
  photo: string | null;
  qr_code: string;
  barcode: string;
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
