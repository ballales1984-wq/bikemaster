import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import LoginForm from './LoginForm.vue'

describe('LoginForm', () => {
  it('validates login credentials before emitting', async () => {
    const wrapper = mount(LoginForm)

    await wrapper.find('#username').setValue('ab')
    await wrapper.find('#password').setValue('123456')
    await wrapper.find('form').trigger('submit')

    expect(wrapper.find('.field-error').text()).toBe('Min 3 characters')
    expect(wrapper.emitted()).not.toHaveProperty('login')
  })

  it('emits login with valid credentials', async () => {
    const wrapper = mount(LoginForm)

    await wrapper.find('#username').setValue('rider')
    await wrapper.find('#password').setValue('secret')
    await wrapper.find('form').trigger('submit')

    expect(wrapper.emitted().login).toEqual([[{ username: 'rider', password: 'secret' }]])
  })

  it('switches to registration mode and validates password length', async () => {
    const wrapper = mount(LoginForm)

    wrapper.vm.mode = 'register'
    await wrapper.vm.$nextTick()
    await wrapper.find('#username').setValue('rider')
    await wrapper.find('#password').setValue('12345')
    await wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Min 6 characters')
    expect(wrapper.emitted()).not.toHaveProperty('register')
  })

  it('toggles password visibility', async () => {
    const wrapper = mount(LoginForm)

    expect(wrapper.find('#password').attributes('type')).toBe('password')

    await wrapper.find('.password-toggle').trigger('click')

    expect(wrapper.find('#password').attributes('type')).toBe('text')
    expect(wrapper.find('.password-toggle').attributes('aria-label')).toBe('Hide password')
  })
})
