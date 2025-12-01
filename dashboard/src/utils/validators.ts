export const isValidUserId = (value: number) => Number.isInteger(value) && value > 0;
export const isValidGatewayCount = (value: number) => Number.isInteger(value) && value >= 1 && value <= 200;
