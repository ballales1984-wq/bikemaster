import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AdminPanel from '../components/AdminPanel.vue'

vi.mock('../utils/api.ts', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}))

describe('AdminPanel', () => {
  it('renders the admin panel title', () => {
    const wrapper = mount(AdminPanel)
    expect(wrapper.find('h2').text()).toContain('Administration')
  })

  it('has admin action cards', () => {
    const wrapper = mount(AdminPanel)
    const cards = wrapper.findAll('.admin-card')
    expect(cards.length).toBeGreaterThanOrEqual(3)
  })

  it('has backup link', () => {
    const wrapper = mount(AdminPanel)
    const backupLink = wrapper.find('a.admin-card')
    expect(backupLink.exists()).toBe(true)
  })
})