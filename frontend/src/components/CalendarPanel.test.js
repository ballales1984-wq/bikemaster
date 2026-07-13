import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

const apiGet = vi.hoisted(() => vi.fn());
const apiPost = vi.hoisted(() => vi.fn());
const apiDelete = vi.hoisted(() => vi.fn());
vi.mock("../utils/api.ts", () => ({ apiGet, apiPost, apiDelete }));

import CalendarPanel from "./CalendarPanel.vue";

function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

const mockAthletes = {
  athletes: [
    { id: 1, name: "Marco Rossi" },
    { id: 2, name: "Luca Bianchi" },
  ],
};

const mockEvents = {
  events: [
    {
      id: 1,
      title: "Morning Ride",
      event_type: "training",
      date: "2026-06-20",
      completed: false,
    },
    {
      id: 2,
      title: "FTP Test",
      event_type: "test",
      date: "2026-06-20",
      completed: false,
    },
    {
      id: 3,
      title: "Race Day",
      event_type: "race",
      date: "2026-06-20",
      completed: true,
    },
    {
      id: 4,
      title: "Recovery",
      event_type: "recovery",
      date: "2026-06-20",
      completed: false,
    },
  ],
};

const mockGoals = {
  goals: "Run 5km per day",
};

describe("CalendarPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads athletes on mount", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    const wrapper = mount(CalendarPanel);
    await flush();
    await flush();

    expect(apiGet).toHaveBeenCalledWith("/api/v1/athletes");
    expect(wrapper.find("select").exists()).toBe(true);
  });

  it("loads events and goals after athlete loads", async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockEvents)
      .mockResolvedValueOnce(mockGoals);

    const wrapper = mount(CalendarPanel);
    await flush();
    await flush();
    await flush();

    const eventsCalls = apiGet.mock.calls.filter(
      (c) => c[0] === "/api/v1/calendar/events",
    );
    expect(eventsCalls.length).toBeGreaterThan(0);
    const goalsCalls = apiGet.mock.calls.filter(
      (c) => c[0] === "/api/v1/athletes/1",
    );
    expect(goalsCalls.length).toBeGreaterThan(0);
  });

  it("renders calendar grid with 7 day headers", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    const wrapper = mount(CalendarPanel);
    await flush();

    expect(wrapper.find(".calendar-grid").exists()).toBe(true);
    expect(wrapper.findAll(".cal-header").length).toBe(7);
  });

  it("navigates to next and previous month via methods", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    const wrapper = mount(CalendarPanel);
    await flush();

    const before = wrapper.find(".month-label").text();

    wrapper.vm.nextMonth();
    await flush();
    expect(wrapper.find(".month-label").text()).not.toBe(before);

    wrapper.vm.prevMonth();
    await flush();
    expect(wrapper.find(".month-label").text()).toBe(before);
  });

  it("goes to today via goToday method", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    const wrapper = mount(CalendarPanel);
    await flush();

    const today = new Date();
    const months = [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ];
    const expected = `${months[today.getMonth()]} ${today.getFullYear()}`;

    wrapper.vm.goToday();
    await flush();

    expect(wrapper.find(".month-label").text()).toBe(expected);
  });

  it("shows event type legend", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    const wrapper = mount(CalendarPanel);
    await flush();

    expect(wrapper.text()).toContain("Training");
    expect(wrapper.text()).toContain("Race");
    expect(wrapper.text()).toContain("Recovery");
  });

  it("opens add form via openAddForDate", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    const wrapper = mount(CalendarPanel);
    await flush();

    wrapper.vm.openAddForDate("2026-06-20");
    await flush();

    expect(wrapper.find("#event-title").exists()).toBe(true);
  });

  it("cancels add form", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    const wrapper = mount(CalendarPanel);
    await flush();

    wrapper.vm.openAddForDate("2026-06-20");
    await flush();
    expect(wrapper.find("#event-title").exists()).toBe(true);

    wrapper.vm.showForm = false;
    await flush();
    expect(wrapper.find("#event-title").exists()).toBe(false);
  });

  it("saves new event via API", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    apiPost.mockResolvedValueOnce({ id: 99 });
    const wrapper = mount(CalendarPanel);
    await flush();

    wrapper.vm.athleteId = 1;
    wrapper.vm.openAddForDate("2026-06-20");
    await flush();

    await wrapper.find("#event-title").setValue("New Ride");
    wrapper.vm.form.event_type = "training";
    await wrapper.find("form").trigger("submit.prevent");
    await flush();

    expect(apiPost).toHaveBeenCalledWith(
      "/api/v1/calendar/events",
      expect.objectContaining({
        title: "New Ride",
        event_type: "training",
        athlete_id: 1,
      }),
    );
  });

  it("opens edit form with existing data", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    const wrapper = mount(CalendarPanel);
    await flush();

    wrapper.vm.openEdit({ title: "Morning Ride", event_type: "training" });
    await flush();

    expect(wrapper.find("#event-title").exists()).toBe(true);
  });

  it("shows recommended objectives", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    const wrapper = mount(CalendarPanel);
    await flush();

    expect(wrapper.text()).toContain("Linked Goals");
    expect(wrapper.text()).toContain("Interval Training");
  });

  it("opens delete modal via askDeleteEvent", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    const wrapper = mount(CalendarPanel);
    await flush();

    wrapper.vm.askDeleteEvent(1);
    await flush();

    expect(wrapper.findComponent({ name: "ConfirmModal" }).exists()).toBe(true);
  });

  it("deletes event via confirm modal", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    apiDelete.mockResolvedValueOnce({});
    const wrapper = mount(CalendarPanel);
    await flush();

    wrapper.vm.askDeleteEvent(1);
    await flush();

    const modal = wrapper.findComponent({ name: "ConfirmModal" });
    await modal.vm.$emit("confirm");
    await flush();

    expect(apiDelete).toHaveBeenCalledWith("/api/v1/calendar/events/1");
  });

  it("eventLabel function maps all event types", async () => {
    apiGet.mockResolvedValueOnce(mockAthletes);
    const wrapper = mount(CalendarPanel);
    await flush();

    expect(wrapper.vm.eventLabel("training")).toBe("Training");
    expect(wrapper.vm.eventLabel("race")).toBe("Race");
    expect(wrapper.vm.eventLabel("recovery")).toBe("Recovery");
    expect(wrapper.vm.eventLabel("goal_deadline")).toBe("Goal");
    expect(wrapper.vm.eventLabel("test")).toBe("Test");
    expect(wrapper.vm.eventLabel("other")).toBe("Other");
  });

  it("changes athlete selection", async () => {
    apiGet
      .mockResolvedValueOnce(mockAthletes)
      .mockResolvedValueOnce(mockEvents)
      .mockResolvedValueOnce(mockGoals);

    const wrapper = mount(CalendarPanel);
    await flush();
    await flush();

    const select = wrapper.find("select");
    await select.setValue(2);
    await flush();

    const calls = apiGet.mock.calls.filter(
      (c) => c[0] === "/api/v1/calendar/events" && c[1]?.athlete_id === 2,
    );
    expect(calls.length).toBeGreaterThan(0);
  });
});
