export type HealthLiveResponse = Readonly<{
  status: "ok";
  service: string;
}>;

export interface LepApiClient {
  getHealthLive(): Promise<HealthLiveResponse>;
}
