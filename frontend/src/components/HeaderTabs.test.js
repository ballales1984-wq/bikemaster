import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import HeaderTabs from './HeaderTabs.vue'

describe('HeaderTabs', () => {
  it('emits active tab updates', async () => {
    const wrapper = mount(HeaderTabs, { props: { active: 'rides' } })

    await wrapper.findAll('button').at(3).trigger('click')

    expect(wrapper.emitted()['update:active']).toEqual([['coach']])
  })

  it('shows admin tab only for admins', () => {
    const userButtons = mount(HeaderTabs, { props: { isAdmin: false } }).findAll('button').map(button => button.text()).join('|')
    const adminButtons = mount(HeaderTabs, { props: { isAdmin: true } }).findAll('button').map(button => button.text()).join('|')

    expect(userButtons).not.toContain('Admin')
    expect(adminButtons).toContain('Admin')
  })

  it('emits logout and displays current user role', async () => {
    const wrapper = mount(HeaderTabs, { props: { isAdmin: true } })

    expect(wrapper.text()).toContain('👑 Admin')

    await wrapper.findAll('button').at(-1).trigger('click')

    expect(wrapper.emitted().logout).toEqual([[]])
  })
})
