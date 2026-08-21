import type { Speaker } from '@/types/capcut';

/**
 * HAR từ CapCut - danh sách giọng nói fallback tiêu biểu
 * Hỗ trợ thị trường Việt Nam
 */
export const fallbackSpeakers: Speaker[] = [
  {
    title: 'Thanh Tùng',
    description: 'Giọng nam miền Bắc trầm ấm',
    speaker: 'ICL_vi_male_thanhtung',
    effectId: '7522976550736694529',
    resourceId: '7522976550736694529',
  },
  {
    title: 'Mai Phương',
    description: 'Giọng nữ miền Bắc nhẹ nhàng',
    speaker: 'ICL_vi_female_maiphuong',
    effectId: '7522976550736727297',
    resourceId: '7522976550736727297',
  },
  {
    title: 'Minh Quân',
    description: 'Giọng nam miền Nam năng động',
    speaker: 'ICL_vi_male_minhquan',
    effectId: '7522976550736743681',
    resourceId: '7522976550736743681',
  },
  {
    title: 'Lan Hương',
    description: 'Giọng nữ miền Nam truyền cảm',
    speaker: 'ICL_vi_female_lanhuong',
    effectId: '7522976550736760065',
    resourceId: '7522976550736760065',
  },
  {
    title: 'Labebe (English)',
    description: 'Giọng nữ tiếng Anh tươi sáng',
    speaker: 'ICL_en_female_jiaoao',
    effectId: '7530105822785899777',
    resourceId: '7530105822785899777',
  },
  {
    title: 'Giọng nữ dễ thương',
    description: 'Giọng nữ dễ thương, cute và đáng yêu',
    speaker: 'BV074_streaming',
    effectId: '7102355709945188865',
    resourceId: '7102355709945188865',
  },
  {
    title: 'Confident Male',
    description: 'Giọng nam tự tin, chuyên nghiệp',
    speaker: 'BV075_streaming',
    effectId: '7102355803792740865',
    resourceId: '7102355803792740865',
  },
];

/**
 * Từ điển giải quyết từ biệt danh người dùng sang resourceId
 */
export const speakerAliases: Record<string, string> = {
  thanhtung: '7522976550736694529',
  maiphuong: '7522976550736727297',
  minhquan: '7522976550736743681',
  lanhuong: '7522976550736760065',
  labebe: '7530105822785899777',
  cutefemale: '7102355709945188865',
  confidentmale: '7102355803792740865',
};
