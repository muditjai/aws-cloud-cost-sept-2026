export const CHAT_MODEL = 'gpt-5.6-luna';
export const MAX_AGENT_STEPS = 10;

interface CurrentWeatherInput {
  city: string;
}

export async function getCurrentWeather(
  { city }: CurrentWeatherInput,
): Promise<string> {
  return `The weather in ${city} is sunny`;
}
