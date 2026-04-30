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
};

export type Employee = {
  id: number;
  full_name: string;
  legal_entity: number;
  user?: number | null;
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

export type AssetConditionJob = {
  id: number;
  asset: number;
  status: string;
  vision_result: Record<string, unknown>;
  llm_summary: string;
  error_message: string;
  source_image: string;
  created_at: string;
  updated_at: string;
};

export type InventorySession = {
  id: number;
  status: string;
  legal_entity: number;
  /** Подпись для списков (с сервера) */
  legal_entity_name?: string;
  location: number | null;
  location_name?: string | null;
  started_by?: number | null;
  conducted_by_employees?: number[];
  started_at?: string;
  finished_at?: string | null;
};

export type InventoryItemResponse = {
  id: number;
  session: number;
  asset: number;
  /** Полный актив с сервера (предпочтительно для отображения) */
  asset_detail?: Asset | null;
  detected: boolean;
  detected_inventory_number: string;
  ocr_text: string;
  condition: string;
  comment: string;
  photo?: string | null;
  scanned_at?: string;
};
