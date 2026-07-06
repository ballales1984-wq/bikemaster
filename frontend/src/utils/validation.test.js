import { describe, it, expect } from "vitest";
import {
  VALID_EXPERIENCE_LEVELS,
  validateAthleteForm,
  validateEmail,
  validateExperienceLevel,
  validateNumber,
  validateRequired,
} from "./validation";

describe("validateRequired", () => {
  it("accepts valid non-empty string", () => {
    expect(validateRequired("test")).toBeNull();
  });

  it("rejects empty string", () => {
    expect(validateRequired("")).not.toBeNull();
  });

  it("rejects string shorter than minLength", () => {
    expect(validateRequired("ab", 3)).not.toBeNull();
  });

  it("rejects whitespace-only string", () => {
    expect(validateRequired("   ")).not.toBeNull();
  });
});

describe("validateEmail", () => {
  it("accepts valid email", () => {
    expect(validateEmail("test@example.com")).toBeNull();
  });

  it("accepts email with subdomain", () => {
    expect(validateEmail("user@mail.example.com")).toBeNull();
  });

  it("rejects email without @", () => {
    expect(validateEmail("test.example.com")).toContain("non valido");
  });

  it("rejects email without domain", () => {
    expect(validateEmail("test@example")).toContain("non valido");
  });

  it("returns null for empty email", () => {
    expect(validateEmail("")).toBeNull();
  });
});

describe("validateNumber", () => {
  it("accepts valid number within range", () => {
    expect(validateNumber(50, 0, 100)).toBeNull();
  });

  it("rejects number below min", () => {
    expect(validateNumber(-5, 0, 100)).toContain("minimo");
  });

  it("rejects number above max", () => {
    expect(validateNumber(150, 0, 100)).toContain("massimo");
  });

  it("rejects NaN", () => {
    expect(validateNumber("abc", 0, 100)).toContain("non valido");
  });
});

describe("validateExperienceLevel", () => {
  it("accepts all valid levels", () => {
    for (const level of VALID_EXPERIENCE_LEVELS) {
      expect(validateExperienceLevel(level)).toBeNull();
    }
  });

  it("rejects invalid level", () => {
    expect(validateExperienceLevel("InvalidLevel")).toContain("non valido");
  });

  it("is case sensitive", () => {
    expect(validateExperienceLevel("beginner")).not.toBeNull();
  });
});

describe("validateAthleteForm", () => {
  it("accepts valid form", () => {
    const form = {
      name: "Mario Rossi",
      age: 35,
      weight_kg: 72.0,
      experience_level: "Intermediate",
    };
    const errors = validateAthleteForm(form);
    expect(Object.keys(errors).length).toBe(0);
  });

  it("rejects name too short", () => {
    const form = {
      name: "A",
      age: 30,
      weight_kg: 70.0,
      experience_level: "Beginner",
    };
    const errors = validateAthleteForm(form);
    expect(errors.name).toBeDefined();
  });

  it("rejects invalid email", () => {
    const form = { name: "Test", age: 30, weight_kg: 70.0, email: "bad-email" };
    const errors = validateAthleteForm(form);
    expect(errors.email).toBeDefined();
  });

  it("accepts valid email", () => {
    const form = {
      name: "Test",
      age: 30,
      weight_kg: 70.0,
      email: "test@example.com",
    };
    const errors = validateAthleteForm(form);
    expect(errors.email).toBeUndefined();
  });

  it("rejects weight out of range", () => {
    const form = {
      name: "Test",
      age: 30,
      weight_kg: 15.0,
      experience_level: "Beginner",
    };
    const errors = validateAthleteForm(form);
    expect(errors.weight_kg).toBeDefined();
  });

  it("rejects age out of range", () => {
    const form = {
      name: "Test",
      age: 9,
      weight_kg: 70.0,
      experience_level: "Beginner",
    };
    const errors = validateAthleteForm(form);
    expect(errors.age).toBeDefined();
  });

  it("rejects invalid experience level", () => {
    const form = {
      name: "Test",
      age: 30,
      weight_kg: 70.0,
      experience_level: "Invalid",
    };
    const errors = validateAthleteForm(form);
    expect(errors.experience_level).toBeDefined();
  });

  it("rejects ftp out of range", () => {
    const form = {
      name: "Test",
      age: 30,
      weight_kg: 70.0,
      ftp_watts: 10,
      experience_level: "Beginner",
    };
    const errors = validateAthleteForm(form);
    expect(errors.ftp_watts).toBeDefined();
  });
});
