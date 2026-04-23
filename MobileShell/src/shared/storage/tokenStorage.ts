import AsyncStorage from "@react-native-async-storage/async-storage";
import { Tokens } from "../types";

const TOKENS_KEY = "smartinv_tokens";

export async function getStoredTokens(): Promise<Tokens | null> {
  const raw = await AsyncStorage.getItem(TOKENS_KEY);
  return raw ? (JSON.parse(raw) as Tokens) : null;
}

export async function setStoredTokens(tokens: Tokens): Promise<void> {
  await AsyncStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
}

export async function clearStoredTokens(): Promise<void> {
  await AsyncStorage.removeItem(TOKENS_KEY);
}
