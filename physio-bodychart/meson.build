project('physio-bodychart', 'c',
  version : '0.1.0',
  default_options : ['warning_level=2', 'c_std=c11'])

gtk4_dep    = dependency('gtk4')
cairo_dep   = dependency('cairo')
rsvg_dep    = dependency('librsvg-2.0')
jsonc_dep   = dependency('json-c')
m_dep       = meson.get_compiler('c').find_library('m', required : false)

sources = files(
  'src/main.c',
  'src/window.c',
  'src/canvas.c',
  'src/input.c',
  'src/stroke.c',
  'src/body_outlines.c',
  'src/svg_views.c',
  'src/overlays.c',
  'src/overlay_svg.c',
  'src/session.c',
  'src/settings.c',
  'src/persistence.c',
  'src/integration.c',
  'src/obj_chart.c',
  'src/report.c',
  'src/svg_regions.c',
  'src/overlay_data/dermatomes.c',
  'src/overlay_data/peripheral.c',
  'src/overlay_data/somatic.c',
)

executable('physio-bodychart',
  sources,
  dependencies : [gtk4_dep, cairo_dep, rsvg_dep, jsonc_dep, m_dep],
  install : true)

install_data('data/com.physio.bodychart.desktop',
  install_dir : get_option('datadir') / 'applications')
